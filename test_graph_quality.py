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
        default="output/graph_quality_benchmark.json",
        help="基准结果 JSON 输出路径",
    )
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    report = build_report(args.max_depth)
    save_report(report, args.output)

    print_report(report)
    print()
    print(f"JSON 报告已写入: {args.output}")


if __name__ == "__main__":
    main()