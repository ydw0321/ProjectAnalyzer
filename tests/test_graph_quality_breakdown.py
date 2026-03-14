from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import argparse

from src.tree import build_report, ensure_graph_data, save_report


def main():
    parser = argparse.ArgumentParser(description="Graph quality unknown breakdown test")
    parser.add_argument("--bootstrap", action="store_true", help="先执行 graph-only 重建图数据")
    parser.add_argument("--max-depth", type=int, default=10, help="可达率计算深度")
    parser.add_argument(
        "--output",
        default="output/quality/graph_quality_breakdown.json",
        help="分类测试结果输出路径",
    )
    parser.add_argument(
        "--show-items",
        type=int,
        default=20,
        help="最多打印多少条 unknown 明细",
    )
    parser.add_argument("--critical-chains", default=None, help="关键链路配置文件路径（JSON）")
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    report = build_report(args.max_depth, critical_chains_path=args.critical_chains)
    save_report(report, args.output)

    counts = report["details"]["unknown_breakdown"]
    items = report["unknown_call_details"]
    actionable_categories = [
        "jdk_core",
        "infra_framework",
        "third_party_lib",
        "internal_shared_lib_missing",
        "true_unresolved",
    ]
    grouped = {
        category: [item for item in items if item.get("category") == category]
        for category in actionable_categories
    }
    top_callers = report["details"].get("unknown_top_callers", [])

    print("=" * 60)
    print("图质量 unknown 分类测试")
    print("=" * 60)
    print(f"总 unknown 数: {counts['total_unknown']}")
    print(f"JDK/标准库 unknown(兼容): {counts['jdk_unknown']}")
    print(f"业务 unknown(兼容): {counts['business_unknown']}")
    print("\n可行动分类统计:")
    for category in actionable_categories:
        print(f"  - {category}: {counts.get(category, 0)}")

    print("\ntrue_unresolved 明细:")
    if grouped["true_unresolved"]:
        for item in grouped["true_unresolved"][:args.show_items]:
            print(f"  - {item['caller_class']}.{item['caller_name']} -> {item['callee_name']}")
    else:
        print("  (无)")

    print("\ninternal_shared_lib_missing 示例:")
    if grouped["internal_shared_lib_missing"]:
        for item in grouped["internal_shared_lib_missing"][:args.show_items]:
            print(f"  - {item['caller_class']}.{item['caller_name']} -> {item['callee_name']}")
    else:
        print("  (无)")

    print("\nTop unknown 调用点:")
    if top_callers:
        for item in top_callers[:args.show_items]:
            print(
                f"  - {item['caller_class']}.{item['caller_name']}: "
                f"{item['count']} ({item.get('ratio', 0.0):.2%}), "
                f"dominant={item.get('dominant_category')}"
            )
    else:
        print("  (无)")

    print(f"\n结果已写入: {args.output}")


if __name__ == "__main__":
    main()