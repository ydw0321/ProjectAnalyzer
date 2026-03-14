"""
explain_metric.py — 指标说明工具

用法:
  python scripts/explain_metric.py broken_chain_rate
  python scripts/explain_metric.py --list
  python scripts/explain_metric.py broken_chain_rate --report output/quality/graph_quality_benchmark.json

输出格式:
  指标名称、公式、当前值（来自最近报告文件）、与上次运行的 delta、可操作建议。
"""
import argparse
import json
import sys
from pathlib import Path
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

# ─── Metric Catalog ───────────────────────────────────────────────────────────

METRIC_CATALOG: dict[str, dict] = {
    # ── call-chain health ──
    "broken_chain_rate": {
        "label": "断链率",
        "formula": "external_unknown_calls / total_calls",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 15%",
        "description": (
            "图中所有调用边里，目标方法无法解析（external_unknown）的比例。"
            "高断链率通常意味着依赖未扫描（jar 包、跨模块依赖）或扫描路径配置错误。"
        ),
        "actions": [
            "确认扫描路径覆盖所有 .java 源文件（含公共库源码）",
            "检查 external_unknown 调用的 top caller，定位集中故障类",
            "用 --explain-metric unknown_top_callers 查看断链热点",
        ],
        "report_path": ["metrics", "broken_chain_rate"],
    },
    "business_broken_chain_rate": {
        "label": "业务断链率",
        "formula": "business_unknown_calls / total_calls",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 5%",
        "description": (
            "非 JDK / 基础框架的 external_unknown 调用比例（即真正属于业务代码但找不到定义的调用）。"
            "比 broken_chain_rate 更能反映业务逻辑覆盖度缺口。"
        ),
        "actions": [
            "运行 test_graph_quality_breakdown.py 查看 true_unresolved / internal_shared_lib_missing 分类",
            "优先补扫 internal_shared_lib_missing 类（内部工具包源码缺失）",
        ],
        "report_path": ["metrics", "business_broken_chain_rate"],
    },
    "reachability_rate": {
        "label": "可达率",
        "formula": "reachable_methods / total_methods",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "> 60%",
        "description": (
            "从所有识别出的入口方法出发，BFS/DFS 可达的方法数 / 图中总方法数。"
            "孤立方法（isolated）会拉低此值。低可达率说明图连通性差或入口识别不足。"
        ),
        "actions": [
            "检查入口方法识别：用 --explain-metric entry_confidence_proxy 查看入口置信度分布",
            "考虑将 Job / Batch 类加入入口白名单",
            "排查 isolated_method_ratio 是否过高（> 30% 需关注）",
        ],
        "report_path": ["metrics", "reachability_rate"],
    },
    "key_chain_hit_rate": {
        "label": "关键链路命中率",
        "formula": "hit_chains / total_critical_chains",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "= 100%",
        "description": (
            "预定义的关键调用链中，至少有一条节点路径能在图中完整找到的比例。"
            "100% 表示图对核心业务流程的覆盖完整；< 100% 需排查断链位置（first_break 字段）。"
        ),
        "actions": [
            "查看 critical_chain_results[].first_break 定位最早断点",
            "用 critical_chain_results[].status=FAIL 的链路重新扫描或补扫相关源码",
        ],
        "report_path": ["metrics", "key_chain_hit_rate"],
    },
    "critical_chain_retention": {
        "label": "关键链路保留率",
        "formula": "total_hop_matches / total_expected_hops",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "> 80%",
        "description": (
            "所有关键链路中，实际找到的跳数 / 期望跳数。"
            "与 key_chain_hit_rate 互补：即使某条链命中，部分跳可能缺失。"
        ),
        "actions": [
            "若 retention 明显低于 hit_rate，说明存在中间跳缺失（中间类未扫描）",
        ],
        "report_path": ["metrics", "critical_chain_retention"],
    },
    "critical_hop_dropout": {
        "label": "关键链路跳丢失率",
        "formula": "1 - critical_chain_retention",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 20%",
        "description": "关键链路跳丢失比例，是 critical_chain_retention 的互补指标。",
        "actions": [],
        "report_path": ["metrics", "critical_hop_dropout"],
    },
    "util_unknown_ratio": {
        "label": "工具层断链占比",
        "formula": "util_unknown_calls / unknown_calls",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 30%",
        "description": (
            "断链调用中来自 util/helper/common 层的比例。"
            "高比例说明工具包依赖集中于未扫描的第三方库。"
        ),
        "actions": [
            "检查 util 层 top caller，确认是否可归类为 jdk_core 或 third_party_lib",
        ],
        "report_path": ["metrics", "util_unknown_ratio"],
    },
    "critical_chain_coverage": {
        "label": "关键链路覆盖率",
        "formula": "critical_methods_in_reachable / total_reachable_methods",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "> 5%",
        "description": (
            "可达方法中，属于关键链路定义的方法占比（critical_chain_reach_share）。"
            "反映关键链路对图整体的代表性。"
        ),
        "actions": [],
        "report_path": ["metrics", "critical_chain_coverage"],
    },
    "critical_definition_presence": {
        "label": "关键方法定义存在率",
        "formula": "defined_critical_methods / total_critical_methods",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "= 100%",
        "description": "关键链路中涉及的方法，在图中有节点定义的比例（不要求有调用边，只要有节点）。",
        "actions": [
            "若 < 100%，说明某些关键类/方法名与图中节点名称不匹配（大小写、包前缀差异）",
        ],
        "report_path": ["metrics", "critical_definition_presence"],
    },
    # ── structural risk ──
    "layer_violation_rate": {
        "label": "分层违规率",
        "formula": "violation_edges / total_call_edges",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 2%",
        "description": (
            "违反分层规则的调用边占总调用边的比例。"
            "违规方向：ui→db 直接跳层、db→bl 逆向、bl→ui 逆向。"
        ),
        "actions": [
            "查看 details.structural_risks.top_layer_violations 定位最严重的违规类对",
            "重构违规类：在 bl→ui 场景通常是事件回调混入，需解耦",
        ],
        "report_path": ["metrics", "layer_violation_rate"],
    },
    "cycle_count": {
        "label": "循环依赖数",
        "formula": "count(class pairs with mutual calls)",
        "unit": "pairs",
        "direction": "lower_is_better",
        "typical_range": "< 50",
        "description": (
            "类级别的双向调用对数（A 调用 B 且 B 调用 A）。"
            "每对计一次。高循环依赖说明模块边界模糊，影响可测试性和可维护性。"
        ),
        "actions": [
            "查看 details.structural_risks.top_cycle_modules 找出最紧耦合的类对",
            "引入接口/事件总线对循环依赖最多的类对进行解耦",
        ],
        "report_path": ["metrics", "cycle_count"],
    },
    "god_method_ratio": {
        "label": "God Method 比例",
        "formula": "methods_with_out_degree>100 / total_methods",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 1%",
        "description": (
            "出度 > 100（直接调用超过 100 个不同目标）的方法占比。"
            "此类方法职责过重，是重构的优先候选。"
        ),
        "actions": [
            "运行 Cypher: MATCH (m:Method)-[r:CALLS]->() WITH m, count(r) AS d WHERE d>100 RETURN m.class_name, m.name, d ORDER BY d DESC LIMIT 20",
            "将 God Method 拆分为若干职责单一的方法",
        ],
        "report_path": ["metrics", "god_method_ratio"],
    },
    "isolated_method_ratio": {
        "label": "孤立方法比例",
        "formula": "methods_with_no_callers_and_no_callees / total_methods",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 20%",
        "description": (
            "没有任何调用关系（既无入边也无出边）的方法占比。"
            "高孤立率可能表示死代码、未扫描依赖、或图构建不完整。"
        ),
        "actions": [
            "先排查是否有扫描遗漏（路径、文件编码）",
            "结合代码审查确认孤立方法是否为真正死代码，可安全删除",
        ],
        "report_path": ["metrics", "isolated_method_ratio"],
    },
    "hotspot_fragility_top20_share": {
        "label": "热点脆弱度 Top20 占比",
        "formula": "sum(in_degree of top20 most-called methods) / sum(all in_degrees)",
        "unit": "%",
        "direction": "lower_is_better",
        "typical_range": "< 30%",
        "description": (
            "被调用最多的 20 个方法的入度之和，占全图入度总和的比例。"
            "高占比说明系统存在少数超级热点，这些方法的任何变更风险都极高。"
        ),
        "actions": [
            "运行 Cypher: MATCH ()-[:CALLS]->(m:Method) WITH m, count(*) AS d ORDER BY d DESC LIMIT 20 RETURN m.class_name, m.name, d",
            "对热点方法加强测试覆盖，变更需要同行评审",
        ],
        "report_path": ["metrics", "hotspot_fragility_top20_share"],
    },
    # ── entry / integrity ──
    "entry_confidence_proxy": {
        "label": "入口置信度代理",
        "formula": "high_confidence_entries / total_entries",
        "unit": "%",
        "direction": "higher_is_better",
        "typical_range": "> 50%",
        "description": (
            "被启发式算法以高置信度识别为入口的方法比例。"
            "低比例说明入口识别规则可能误判，或项目缺乏标准入口命名约定。"
        ),
        "actions": [
            "查看 entry_rule_stats 了解哪条规则贡献最多分",
            "在 query_service.py 中为项目特有入口类型添加自定义规则",
        ],
        "report_path": ["metrics", "entry_confidence_proxy"],
    },
}

# ─── helpers ──────────────────────────────────────────────────────────────────

DEFAULT_REPORT = Path("output/quality/graph_quality_benchmark.json")
PREV_REPORTS = [
    Path("output/quality/graph_quality_benchmark.reins.quick.json"),
]


def _load_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_nested(data: dict, path: list[str]):
    """Walk nested dicts; return None if missing."""
    node = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _fmt_value(value, unit: str) -> str:
    if value is None:
        return "N/A"
    if unit == "%":
        if isinstance(value, float) and value <= 1.0:
            return f"{value:.2%}"
        return f"{value:.2f}%"
    return str(value)


def explain(metric_name: str, report_path: Path) -> None:
    meta = METRIC_CATALOG.get(metric_name)
    if meta is None:
        print(f"❌ 未知指标: {metric_name!r}")
        print("   使用 --list 查看所有可用指标")
        sys.exit(1)

    report = _load_report(report_path)
    current_raw = _get_nested(report, meta["report_path"])
    unit = meta["unit"]

    # Try to find a previous report for delta
    prev_value = None
    for prev_path in PREV_REPORTS:
        if prev_path != report_path:
            prev_report = _load_report(prev_path)
            prev_raw = _get_nested(prev_report, meta["report_path"])
            if prev_raw is not None:
                prev_value = prev_raw
                break

    print(f"\n{'─'*60}")
    print(f"  {meta['label']}  ({metric_name})")
    print(f"{'─'*60}")
    print(f"  公式:      {meta['formula']}")
    print(f"  单位:      {unit}")
    print(f"  方向:      {'↓ 越低越好' if meta['direction'] == 'lower_is_better' else '↑ 越高越好'}")
    print(f"  参考范围:  {meta['typical_range']}")
    print()
    print(f"  当前值:    {_fmt_value(current_raw, unit)}")
    if prev_value is not None:
        if isinstance(current_raw, (int, float)) and isinstance(prev_value, (int, float)):
            delta = current_raw - prev_value
            sign = "+" if delta >= 0 else ""
            print(f"  上次值:    {_fmt_value(prev_value, unit)}  (delta: {sign}{_fmt_value(delta, unit)})")
    if not report.get("timestamp"):
        print(f"  (报告文件: {report_path} — 未找到或缺少 timestamp)")
    else:
        print(f"  报告时间:  {report.get('timestamp', 'N/A')}")
    print()
    print(f"  说明:")
    for line in meta["description"].split("。"):
        line = line.strip()
        if line:
            print(f"    {line}。")
    print()
    if meta["actions"]:
        print(f"  可操作建议:")
        for action in meta["actions"]:
            print(f"    • {action}")
    print()


def list_metrics() -> None:
    print(f"\n{'─'*60}")
    print(f"  {'指标名称':<40} {'标签'}")
    print(f"{'─'*60}")
    for name, meta in METRIC_CATALOG.items():
        print(f"  {name:<40} {meta['label']}")
    print()


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="显示指标含义、公式及当前值",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("metric", nargs="?", help="指标名称（如 broken_chain_rate）")
    parser.add_argument("--list", action="store_true", help="列出所有已知指标")
    parser.add_argument(
        "--report",
        metavar="PATH",
        default=str(DEFAULT_REPORT),
        help=f"基准报告 JSON 文件路径（默认: {DEFAULT_REPORT}）",
    )
    args = parser.parse_args()

    if args.list:
        list_metrics()
        return

    if not args.metric:
        parser.print_help()
        sys.exit(1)

    explain(args.metric, Path(args.report))


if __name__ == "__main__":
    main()
