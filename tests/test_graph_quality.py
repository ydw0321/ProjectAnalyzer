from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import argparse

from src.tree import build_report, ensure_graph_data, print_report, save_report


def main():
    parser = argparse.ArgumentParser(description="Graph quality benchmark")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="执行 main.py --graph-only 以先重建图数据",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="计算可达率时使用的最大调用深度",
    )
    parser.add_argument(
        "--output",
        default="output/quality/graph_quality_benchmark.json",
        help="基准结果 JSON 输出路径",
    )
    parser.add_argument(
        "--critical-chains",
        default=None,
        help="关键链路配置文件路径（JSON），不传则使用 config/critical_chains.json 或内置默认",
    )
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    report = build_report(args.max_depth, critical_chains_path=args.critical_chains)
    save_report(report, args.output)

    print_report(report)
    print()
    print(f"JSON 报告已写入: {args.output}")


if __name__ == "__main__":
    main()