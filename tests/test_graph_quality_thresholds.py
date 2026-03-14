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
    parser.add_argument("--min-critical-chain-retention", type=float, default=1.0, help="关键链保留率下限")
    parser.add_argument("--max-critical-hop-dropout", type=float, default=0.1, help="关键跳点丢失率上限")
    parser.add_argument("--max-util-unknown-ratio", type=float, default=0.85, help="util unknown 占比上限")
    parser.add_argument("--min-critical-chain-coverage", type=float, default=0.0, help="关键链覆盖率下限")
    parser.add_argument("--min-critical-definition-presence", type=float, default=0.0, help="关键链定义命中率下限")
    parser.add_argument("--max-layer-violation-rate", type=float, default=None, help="分层违规率上限")
    parser.add_argument("--max-cycle-count", type=float, default=None, help="循环依赖数上限")
    parser.add_argument("--max-god-method-ratio", type=float, default=None, help="God method 比例上限")
    parser.add_argument("--max-isolated-method-ratio", type=float, default=None, help="孤立方法比例上限")
    parser.add_argument("--max-hotspot-fragility-top20-share", type=float, default=None, help="热点脆弱度 Top20 占比上限")
    parser.add_argument("--critical-chains", default=None, help="关键链路配置文件路径（JSON）")
    parser.add_argument(
        "--output",
        default="output/quality/graph_quality_thresholds.json",
        help="阈值测试结果输出路径",
    )
    args = parser.parse_args()

    ensure_graph_data(args.bootstrap)
    report = build_report(args.max_depth, critical_chains_path=args.critical_chains)
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
        (
            metrics["critical_chain_retention"] >= args.min_critical_chain_retention,
            f"关键链保留率低于阈值: {metrics['critical_chain_retention']:.2%} < {args.min_critical_chain_retention:.2%}",
        ),
        (
            metrics["critical_hop_dropout"] <= args.max_critical_hop_dropout,
            f"关键跳点丢失率超阈值: {metrics['critical_hop_dropout']:.2%} > {args.max_critical_hop_dropout:.2%}",
        ),
        (
            metrics["util_unknown_ratio"] <= args.max_util_unknown_ratio,
            f"util unknown 占比超阈值: {metrics['util_unknown_ratio']:.2%} > {args.max_util_unknown_ratio:.2%}",
        ),
        (
            metrics["critical_chain_coverage"] >= args.min_critical_chain_coverage,
            f"关键链覆盖率低于阈值: {metrics['critical_chain_coverage']:.2%} < {args.min_critical_chain_coverage:.2%}",
        ),
        (
            metrics["critical_definition_presence"] >= args.min_critical_definition_presence,
            f"关键链定义命中率低于阈值: {metrics['critical_definition_presence']:.2%} < {args.min_critical_definition_presence:.2%}",
        ),
    ]

    optional_checks = []
    if args.max_layer_violation_rate is not None:
        optional_checks.append(
            (
                metrics["layer_violation_rate"] <= args.max_layer_violation_rate,
                f"分层违规率超阈值: {metrics['layer_violation_rate']:.2%} > {args.max_layer_violation_rate:.2%}",
            )
        )
    if args.max_cycle_count is not None:
        optional_checks.append(
            (
                metrics["cycle_count"] <= args.max_cycle_count,
                f"循环依赖数超阈值: {metrics['cycle_count']} > {args.max_cycle_count}",
            )
        )
    if args.max_god_method_ratio is not None:
        optional_checks.append(
            (
                metrics["god_method_ratio"] <= args.max_god_method_ratio,
                f"God method 比例超阈值: {metrics['god_method_ratio']:.2%} > {args.max_god_method_ratio:.2%}",
            )
        )
    if args.max_isolated_method_ratio is not None:
        optional_checks.append(
            (
                metrics["isolated_method_ratio"] <= args.max_isolated_method_ratio,
                f"孤立方法比例超阈值: {metrics['isolated_method_ratio']:.2%} > {args.max_isolated_method_ratio:.2%}",
            )
        )
    if args.max_hotspot_fragility_top20_share is not None:
        optional_checks.append(
            (
                metrics["hotspot_fragility_top20_share"] <= args.max_hotspot_fragility_top20_share,
                f"热点脆弱度 Top20 占比超阈值: {metrics['hotspot_fragility_top20_share']:.2%} > {args.max_hotspot_fragility_top20_share:.2%}",
            )
        )
    checks.extend(optional_checks)

    failures = [message for passed, message in checks if not passed]

    print("=" * 60)
    print("图质量阈值回归测试")
    print("=" * 60)
    print(f"断链率: {metrics['broken_chain_rate']:.2%}")
    print(f"业务断链率: {metrics['business_broken_chain_rate']:.2%}")
    print(f"可达率: {metrics['reachability_rate']:.2%}")
    print(f"关键链路命中率: {metrics['key_chain_hit_rate']:.2%}")
    print(f"关键链定义命中率: {metrics['critical_definition_presence']:.2%}")
    print(f"关键链路逐跳命中率: {details['key_chain_hop_hit_rate']:.2%}")
    print(f"关键链覆盖率: {metrics['critical_chain_coverage']:.2%}")
    print(f"关键链保留率: {metrics['critical_chain_retention']:.2%}")
    print(f"关键跳点丢失率: {metrics['critical_hop_dropout']:.2%}")
    print(f"分层违规率: {metrics['layer_violation_rate']:.2%}")
    print(f"循环依赖数: {metrics['cycle_count']}")
    print(f"God method 比例: {metrics['god_method_ratio']:.2%}")
    print(f"孤立方法比例: {metrics['isolated_method_ratio']:.2%}")
    print(f"热点脆弱度 Top20 占比: {metrics['hotspot_fragility_top20_share']:.2%}")
    print(f"util unknown 占比: {metrics['util_unknown_ratio']:.2%}")

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