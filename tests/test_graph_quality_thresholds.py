from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import argparse
import sys

from src.tree import build_report, ensure_graph_data, save_report


def main():
    parser = argparse.ArgumentParser(description="Graph quality threshold test")
    parser.add_argument("--bootstrap", action="store_true", help="先执行 graph-only 重建图数据")
    parser.add_argument("--max-depth", type=int, default=10, help="可达率计算深度")
    parser.add_argument("--max-broken-chain-rate", type=float, default=0.35, help="总断链率上限")
    parser.add_argument("--max-business-broken-chain-rate", type=float, default=0.02, help="业务断链率上限")
    parser.add_argument("--min-reachability-rate", type=float, default=0.75, help="可达率下限")
    parser.add_argument("--min-key-chain-hit-rate", type=float, default=1.0, help="关键链路命中率下限")
    parser.add_argument("--min-key-chain-hop-hit-rate", type=float, default=1.0, help="关键链路逐跳命中率下限")
    parser.add_argument(
        "--output",
        default="output/quality/graph_quality_thresholds.json",
        help="阈值测试结果输出路径",
    )
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    report = build_report(args.max_depth)
    save_report(report, args.output)

    metrics = report["metrics"]
    details = report["details"]

    checks = [
        (
            metrics["broken_chain_rate"] <= args.max_broken_chain_rate,
            f"断链率超阈值: {metrics['broken_chain_rate']:.2%} > {args.max_broken_chain_rate:.2%}",
        ),
        (
            metrics["business_broken_chain_rate"] <= args.max_business_broken_chain_rate,
            f"业务断链率超阈值: {metrics['business_broken_chain_rate']:.2%} > {args.max_business_broken_chain_rate:.2%}",
        ),
        (
            metrics["reachability_rate"] >= args.min_reachability_rate,
            f"可达率低于阈值: {metrics['reachability_rate']:.2%} < {args.min_reachability_rate:.2%}",
        ),
        (
            metrics["key_chain_hit_rate"] >= args.min_key_chain_hit_rate,
            f"关键链路命中率低于阈值: {metrics['key_chain_hit_rate']:.2%} < {args.min_key_chain_hit_rate:.2%}",
        ),
        (
            details["key_chain_hop_hit_rate"] >= args.min_key_chain_hop_hit_rate,
            f"关键链路逐跳命中率低于阈值: {details['key_chain_hop_hit_rate']:.2%} < {args.min_key_chain_hop_hit_rate:.2%}",
        ),
    ]

    failures = [message for passed, message in checks if not passed]

    print("=" * 60)
    print("图质量阈值回归测试")
    print("=" * 60)
    print(f"断链率: {metrics['broken_chain_rate']:.2%}")
    print(f"业务断链率: {metrics['business_broken_chain_rate']:.2%}")
    print(f"可达率: {metrics['reachability_rate']:.2%}")
    print(f"关键链路命中率: {metrics['key_chain_hit_rate']:.2%}")
    print(f"关键链路逐跳命中率: {details['key_chain_hop_hit_rate']:.2%}")

    if failures:
        print("\n❌ 阈值测试失败:")
        for failure in failures:
            print(f"  - {failure}")
        print(f"\n结果已写入: {args.output}")
        sys.exit(1)

    print("\n✅ 阈值测试通过")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    main()