from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import argparse

from src.tree import (
    build_report,
    ensure_graph_data,
    enrich_with_delta,
    load_prev_report,
    print_report,
    save_critical_chain_candidates,
    save_report,
    suggest_critical_chains,
)


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
    parser.add_argument(
        "--suggest-critical-chains-output",
        default=None,
        help="自动生成关键链候选并保存到该 JSON 路径（可用于后续人工筛选）",
    )
    parser.add_argument(
        "--suggest-chain-count",
        type=int,
        default=10,
        help="自动生成关键链候选数量",
    )
    parser.add_argument(
        "--suggest-max-hops",
        type=int,
        default=5,
        help="自动生成关键链候选时每条链最大跳数",
    )
    parser.add_argument(
        "--suggest-max-per-core-prefix",
        type=int,
        default=2,
        help="候选链多样性控制：同一核心前缀最多保留数量",
    )
    parser.add_argument(
        "--suggest-core-prefix-len",
        type=int,
        default=3,
        help="候选链多样性控制：核心前缀长度（从第2跳开始计）",
    )
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    prev_report = load_prev_report(args.output)
    report = build_report(args.max_depth, critical_chains_path=args.critical_chains)
    enrich_with_delta(report, prev_report)
    save_report(report, args.output)

    print_report(report)
    print()
    print(f"JSON 报告已写入: {args.output}")

    if args.suggest_critical_chains_output:
        candidates = suggest_critical_chains(
            chain_count=args.suggest_chain_count,
            max_hops=args.suggest_max_hops,
            max_per_core_prefix=args.suggest_max_per_core_prefix,
            core_prefix_len=args.suggest_core_prefix_len,
        )
        save_critical_chain_candidates(candidates, args.suggest_critical_chains_output)
        print(f"关键链候选已写入: {args.suggest_critical_chains_output}")


if __name__ == "__main__":
    main()