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
    business_items = [item for item in items if item["category"] == "business_unknown"]
    jdk_items = [item for item in items if item["category"] == "jdk_unknown"]

    print("=" * 60)
    print("图质量 unknown 分类测试")
    print("=" * 60)
    print(f"总 unknown 数: {counts['total_unknown']}")
    print(f"JDK/标准库 unknown: {counts['jdk_unknown']}")
    print(f"业务 unknown: {counts['business_unknown']}")

    print("\n业务 unknown 明细:")
    if business_items:
        for item in business_items[:args.show_items]:
            print(f"  - {item['caller_class']}.{item['caller_name']} -> {item['callee_name']}")
    else:
        print("  (无)")

    print("\nJDK/标准库 unknown 示例:")
    if jdk_items:
        for item in jdk_items[:args.show_items]:
            print(f"  - {item['caller_class']}.{item['caller_name']} -> {item['callee_name']}")
    else:
        print("  (无)")

    print(f"\n结果已写入: {args.output}")


if __name__ == "__main__":
    main()