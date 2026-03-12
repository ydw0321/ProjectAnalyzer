"""
专项测试：面向 test_java_ssh 的图生成阶段深度诊断。

目标：比普通通过/失败测试更全面地暴露图生成问题，聚焦以下维度：
1) 图结构完整性（Class/Method/BELONGS_TO/CALLS）
2) 层级识别覆盖（other 比例与 action/interceptor/job 等老系统目录）
3) 入口方法可达性（是否存在入口孤点）
4) external_unknown 质量（JDK 噪声 vs 真实业务漏链）
5) unknown 可补链潜力（是否存在可唯一匹配但未回填）
"""

import argparse
import json
import os

from main import main
from src.config import Config
from src.tree import build_report
from src.tree.query_service import GraphQueryService


def _run_graph_pipeline_for_ssh(bootstrap: bool):
    if not bootstrap:
        return

    old_path = Config.PROJECT_PATH
    try:
        Config.PROJECT_PATH = "./test_java_ssh"
        main(enable_llm=False)
    finally:
        Config.PROJECT_PATH = old_path


def _collect_structure_diagnostics(query: GraphQueryService):
    with query.driver.session() as session:
        counts_row = session.run(
            """
            MATCH (c:Class)
            WITH count(c) AS class_count
            MATCH (m:Method)
            WITH class_count, count(m) AS method_count
            MATCH ()-[b:BELONGS_TO]->()
            WITH class_count, method_count, count(b) AS belongs_count
            MATCH ()-[r:CALLS]->()
            RETURN class_count, method_count, belongs_count, count(r) AS call_count
            """
        ).single()

        orphan_methods = session.run(
            """
            MATCH (m:Method)
            WHERE NOT (m)-[:BELONGS_TO]->(:Class)
            RETURN count(m) AS c
            """
        ).single()["c"]

        classes_without_methods = session.run(
            """
            MATCH (c:Class)
            WHERE NOT (:Method)-[:BELONGS_TO]->(c)
            RETURN count(c) AS c
            """
        ).single()["c"]

    return {
        "class_count": counts_row["class_count"],
        "method_count": counts_row["method_count"],
        "belongs_count": counts_row["belongs_count"],
        "call_count": counts_row["call_count"],
        "orphan_methods": orphan_methods,
        "classes_without_methods": classes_without_methods,
    }


def _collect_layer_diagnostics(query: GraphQueryService, total_classes: int):
    layer_stats = query.get_layer_statistics()
    layer_map = {item["layer"]: item["class_count"] for item in layer_stats}
    other_count = layer_map.get("other", 0)
    other_ratio = (other_count / total_classes) if total_classes else 0.0

    return {
        "layer_counts": layer_map,
        "other_count": other_count,
        "other_ratio": other_ratio,
    }


def _collect_entry_reachability_diagnostics(query: GraphQueryService):
    entry_methods = query.get_entry_methods()
    zero_out_entries = []

    for entry in entry_methods:
        calls = query.get_method_calls(entry["method_name"], entry.get("class_name"))
        if not calls:
            zero_out_entries.append(
                {
                    "class": entry.get("class_name"),
                    "method": entry.get("method_name"),
                }
            )

    return {
        "entry_method_count": len(entry_methods),
        "entry_without_downstream_count": len(zero_out_entries),
        "entry_without_downstream": zero_out_entries,
    }


def _collect_unknown_resolve_potential(query: GraphQueryService):
    with query.driver.session() as session:
        rows = session.run(
            """
            MATCH (caller:Method)-[:CALLS {type: 'external_unknown'}]->(ext:ExternalMethod)
            OPTIONAL MATCH (candidate:Method {name: ext.name})
            WITH caller, ext, count(candidate) AS candidate_count
            RETURN caller.class_name AS caller_class,
                   caller.name AS caller_name,
                   ext.name AS callee_name,
                   candidate_count
            ORDER BY candidate_count DESC, caller.class_name, caller.name
            """
        )
        items = [dict(record) for record in rows]

    uniquely_matchable = [item for item in items if item["candidate_count"] == 1]
    ambiguous_matchable = [item for item in items if item["candidate_count"] > 1]

    return {
        "unknown_items": len(items),
        "unique_matchable": len(uniquely_matchable),
        "ambiguous_matchable": len(ambiguous_matchable),
        "sample_unique_matchable": uniquely_matchable[:20],
        "sample_ambiguous_matchable": ambiguous_matchable[:20],
    }


def build_ssh_graph_diagnostics(max_depth: int):
    with GraphQueryService() as query:
        report = build_report(max_depth=max_depth)
        structure = _collect_structure_diagnostics(query)
        layer = _collect_layer_diagnostics(query, structure["class_count"])
        entry = _collect_entry_reachability_diagnostics(query)
        unknown_potential = _collect_unknown_resolve_potential(query)

    return {
        "core_quality": report,
        "structure": structure,
        "layer_diagnostics": layer,
        "entry_diagnostics": entry,
        "unknown_resolve_potential": unknown_potential,
    }


def _derive_optimization_hints(diagnostics):
    hints = []

    other_ratio = diagnostics["layer_diagnostics"]["other_ratio"]
    if other_ratio > 0.20:
        hints.append(
            "Layer 识别覆盖偏低：建议将 action/interceptor/job/form/legacy 等目录加入基础层映射，"
            "并为 SSH 项目引入可配置层级规则。"
        )

    entry_without_downstream = diagnostics["entry_diagnostics"]["entry_without_downstream_count"]
    if entry_without_downstream > 0:
        hints.append(
            "存在入口孤点方法：建议在调用树入口选择中优先业务 action 方法，"
            "并排除纯响应构造或工具方法。"
        )

    business_unknown = diagnostics["core_quality"]["details"]["unknown_breakdown"]["business_unknown"]
    if business_unknown > 0:
        hints.append(
            "仍存在业务 unknown：建议增强 lambda/stream 链式调用解析，"
            "并加入局部变量类型流追踪。"
        )

    if diagnostics["unknown_resolve_potential"]["ambiguous_matchable"] > 0:
        hints.append(
            "存在可候选但歧义 unknown：建议为 Method 引入 signature 维度（参数类型），"
            "降低同名方法匹配歧义。"
        )

    if diagnostics["structure"]["orphan_methods"] > 0:
        hints.append(
            "检测到 orphan methods：建议在图生成后增加一致性校验并输出异常列表。"
        )

    if not hints:
        hints.append("当前图生成结构健康，可进一步通过更复杂样例扩展测试边界。")

    return hints


def run_test(max_depth: int, bootstrap: bool, output: str):
    _run_graph_pipeline_for_ssh(bootstrap)
    diagnostics = build_ssh_graph_diagnostics(max_depth=max_depth)
    diagnostics["optimization_hints"] = _derive_optimization_hints(diagnostics)

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output, "w", encoding="utf-8") as file:
        json.dump(diagnostics, file, ensure_ascii=False, indent=2)

    core = diagnostics["core_quality"]
    print("=" * 60)
    print("test_java_ssh 图生成阶段深度诊断")
    print("=" * 60)
    print(
        f"断链率: {core['metrics']['broken_chain_rate']:.2%}, "
        f"业务断链率: {core['metrics']['business_broken_chain_rate']:.2%}, "
        f"可达率: {core['metrics']['reachability_rate']:.2%}"
    )
    print(
        f"关键链路命中率: {core['metrics']['key_chain_hit_rate']:.2%}, "
        f"逐跳命中率: {core['details']['key_chain_hop_hit_rate']:.2%}"
    )
    print(
        f"Class/Method/BELONGS_TO/CALLS: "
        f"{diagnostics['structure']['class_count']}/"
        f"{diagnostics['structure']['method_count']}/"
        f"{diagnostics['structure']['belongs_count']}/"
        f"{diagnostics['structure']['call_count']}"
    )
    print(
        f"other 层比例: {diagnostics['layer_diagnostics']['other_ratio']:.2%}, "
        f"入口孤点: {diagnostics['entry_diagnostics']['entry_without_downstream_count']}, "
        f"业务 unknown: {core['details']['unknown_breakdown']['business_unknown']}"
    )
    print("\n优化建议:")
    for idx, hint in enumerate(diagnostics["optimization_hints"], 1):
        print(f"  {idx}. {hint}")

    print(f"\n诊断报告已写入: {output}")


def main_cli():
    parser = argparse.ArgumentParser(description="test_java_ssh graph generation diagnostics")
    parser.add_argument("--max-depth", type=int, default=12, help="可达率与调用链计算深度")
    parser.add_argument("--bootstrap", action="store_true", help="是否先执行 test_java_ssh graph-only 构图")
    parser.add_argument(
        "--output",
        default="output/ssh_graph_generation_diagnostics.json",
        help="诊断输出 JSON 路径",
    )
    args = parser.parse_args()

    run_test(max_depth=args.max_depth, bootstrap=args.bootstrap, output=args.output)


if __name__ == "__main__":
    main_cli()