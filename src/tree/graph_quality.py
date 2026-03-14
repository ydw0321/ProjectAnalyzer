import json
import os
import subprocess
import sys
import time

from src.tree.query_service import GraphQueryService


CRITICAL_CHAINS = [
    {
        "name": "order_create_main_flow",
        "hops": [
            ("OrderController", "createOrder"),
            ("OrderBiz", "submitOrder"),
            ("OrderFacade", "placeOrder"),
            ("OrderService", "createOrder"),
            ("OrderDal", "insert"),
        ],
    },
    {
        "name": "order_cancel_main_flow",
        "hops": [
            ("OrderController", "cancelOrder"),
            ("OrderBiz", "handleOrderCancellation"),
            ("OrderFacade", "cancelOrder"),
            ("OrderService", "cancelOrder"),
            ("OrderDal", "update"),
        ],
    },
    {
        "name": "product_query_main_flow",
        "hops": [
            ("ProductController", "getProduct"),
            ("ProductBiz", "queryProduct"),
            ("ProductFacade", "getProductDetails"),
            ("ProductService", "getProduct"),
            ("ProductDal", "findById"),
        ],
    },
    {
        "name": "product_list_main_flow",
        "hops": [
            ("ProductController", "listProducts"),
            ("ProductBiz", "listProductsByCategory"),
            ("ProductFacade", "getProductsByCategory"),
            ("ProductService", "getProductsByCategory"),
            ("ProductDal", "findByCategory"),
        ],
    },
    {
        "name": "user_register_main_flow",
        "hops": [
            ("UserController", "register"),
            ("UserBiz", "registerUser"),
            ("UserFacade", "register"),
            ("UserService", "registerUser"),
            ("UserDal", "insert"),
        ],
    },
    {
        "name": "user_list_main_flow",
        "hops": [
            ("UserController", "listUsers"),
            ("UserBiz", "fetchAllUsers"),
            ("UserFacade", "getAllUsers"),
            ("UserService", "getAllUsers"),
            ("UserDal", "findAll"),
        ],
    },
]


JDK_LIKELY_METHODS = {
    "abs",
    "add",
    "before",
    "compareTo",
    "contains",
    "currentTimeMillis",
    "divide",
    "endsWith",
    "equals",
    "filter",
    "findFirst",
    "format",
    "getMessage",
    "getStackTrace",
    "getTime",
    "isEmpty",
    "iterator",
    "length",
    "multiply",
    "nanoTime",
    "now",
    "orElse",
    "randomUUID",
    "remove",
    "setScale",
    "size",
    "split",
    "startsWith",
    "stream",
    "substring",
    "subtract",
    "toString",
    "trim",
    "valueOf",
}


def ensure_graph_data(bootstrap=False):
    if not bootstrap:
        return

    subprocess.run([sys.executable, "main.py", "--graph-only"], check=True)


def collect_reachable_methods(query, max_depth):
    entry_methods = query.get_entry_methods()
    reachable_methods = set()

    for entry in entry_methods:
        entry_key = (entry.get("class_name"), entry.get("method_name"))
        reachable_methods.add(entry_key)

        downstream = query.get_downstream_calls(
            entry["method_name"],
            entry.get("class_name"),
            max_depth=max_depth,
        )
        for node in downstream:
            if node.get("class") and node.get("method"):
                reachable_methods.add((node["class"], node["method"]))

    return entry_methods, reachable_methods


def evaluate_critical_chains(query):
    total_chains = len(CRITICAL_CHAINS)
    full_hit_chains = 0
    total_hops = 0
    hit_hops = 0
    chain_results = []

    for chain in CRITICAL_CHAINS:
        hop_results = []
        is_full_hit = True

        for source, target in zip(chain["hops"], chain["hops"][1:]):
            total_hops += 1
            calls = query.get_method_calls(source[1], source[0])
            matched = any(
                call.get("callee_name") == target[1]
                and call.get("callee_class") == target[0]
                for call in calls
            )

            if matched:
                hit_hops += 1
            else:
                is_full_hit = False

            hop_results.append(
                {
                    "from": {"class": source[0], "method": source[1]},
                    "to": {"class": target[0], "method": target[1]},
                    "matched": matched,
                }
            )

        if is_full_hit:
            full_hit_chains += 1

        chain_results.append(
            {
                "name": chain["name"],
                "full_hit": is_full_hit,
                "matched_hops": sum(1 for hop in hop_results if hop["matched"]),
                "total_hops": len(hop_results),
                "hops": hop_results,
            }
        )

    return {
        "full_hit_chains": full_hit_chains,
        "total_chains": total_chains,
        "hit_hops": hit_hops,
        "total_hops": total_hops,
        "chains": chain_results,
    }


def classify_unknown_method(method_name):
    if method_name in JDK_LIKELY_METHODS:
        return "jdk_unknown"
    return "business_unknown"


def _is_util_class_name(class_name):
    name = (class_name or "").lower()
    util_markers = ("util", "utils", "helper", "common")
    return any(marker in name for marker in util_markers)


def get_unknown_call_breakdown(query):
    with query.driver.session() as session:
        result = session.run(
            """
            MATCH (caller:Method)-[r:CALLS {type: 'external_unknown'}]->(callee:ExternalMethod)
            RETURN caller.class_name AS caller_class,
                   caller.name AS caller_name,
                   callee.name AS callee_name,
                   r.unknown_category AS rel_unknown_category,
                   callee.category AS node_unknown_category
            ORDER BY caller.class_name, caller.name, callee.name
            """
        )
        rows = [dict(record) for record in result]

    classified_rows = []
    counts = {"jdk_unknown": 0, "business_unknown": 0}

    for row in rows:
        category = row.get("rel_unknown_category") or row.get("node_unknown_category") or classify_unknown_method(row["callee_name"])
        counts[category] += 1
        row["category"] = category
        classified_rows.append(row)

    counts["total_unknown"] = len(classified_rows)
    return {"counts": counts, "items": classified_rows}


def build_report(max_depth=10):
    with GraphQueryService() as query:
        all_methods = query.get_all_methods()
        call_stats = query.get_call_statistics()
        entry_methods, reachable_methods = collect_reachable_methods(query, max_depth)
        chain_eval = evaluate_critical_chains(query)
        unknown_breakdown = get_unknown_call_breakdown(query)

    total_methods = len(all_methods)
    total_calls = call_stats.get("total", 0)
    unknown_calls = call_stats.get("external_unknown", 0)
    business_unknown = unknown_breakdown["counts"].get("business_unknown", 0)
    unknown_items = unknown_breakdown["items"]

    critical_classes = {
        class_name
        for chain in CRITICAL_CHAINS
        for class_name, _ in chain["hops"]
    }
    critical_unknown_calls = sum(
        1 for item in unknown_items if item.get("caller_class") in critical_classes
    )
    util_unknown_calls = sum(
        1 for item in unknown_items if _is_util_class_name(item.get("caller_class"))
    )

    broken_chain_rate = (unknown_calls / total_calls) if total_calls else 0.0
    business_broken_chain_rate = (business_unknown / total_calls) if total_calls else 0.0
    reachability_rate = (len(reachable_methods) / total_methods) if total_methods else 0.0
    key_chain_hit_rate = (
        chain_eval["full_hit_chains"] / chain_eval["total_chains"]
        if chain_eval["total_chains"]
        else 0.0
    )
    key_chain_hop_hit_rate = (
        chain_eval["hit_hops"] / chain_eval["total_hops"]
        if chain_eval["total_hops"]
        else 0.0
    )
    critical_chain_retention = key_chain_hop_hit_rate
    critical_hop_dropout = 1.0 - critical_chain_retention
    util_unknown_ratio = (util_unknown_calls / unknown_calls) if unknown_calls else 0.0

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "broken_chain_rate": broken_chain_rate,
            "business_broken_chain_rate": business_broken_chain_rate,
            "reachability_rate": reachability_rate,
            "key_chain_hit_rate": key_chain_hit_rate,
            "critical_chain_retention": critical_chain_retention,
            "critical_hop_dropout": critical_hop_dropout,
            "util_unknown_ratio": util_unknown_ratio,
        },
        "details": {
            "total_methods": total_methods,
            "reachable_methods": len(reachable_methods),
            "entry_method_count": len(entry_methods),
            "total_calls": total_calls,
            "unknown_calls": unknown_calls,
            "internal_calls": call_stats.get("internal", 0),
            "external_calls": call_stats.get("external", 0),
            "key_chain_hop_hit_rate": key_chain_hop_hit_rate,
            "matched_key_chains": chain_eval["full_hit_chains"],
            "total_key_chains": chain_eval["total_chains"],
            "matched_key_hops": chain_eval["hit_hops"],
            "total_key_hops": chain_eval["total_hops"],
            "critical_unknown_calls": critical_unknown_calls,
            "util_unknown_calls": util_unknown_calls,
            "unknown_breakdown": unknown_breakdown["counts"],
        },
        "critical_chain_results": chain_eval["chains"],
        "unknown_call_details": unknown_breakdown["items"],
    }


def print_report(report):
    metrics = report["metrics"]
    details = report["details"]
    unknown_breakdown = details["unknown_breakdown"]

    print("=" * 60)
    print("图质量基准测试")
    print("=" * 60)
    print(f"时间: {report['timestamp']}")
    print()
    print("核心指标:")
    print(f"  断链率: {metrics['broken_chain_rate']:.2%} ({details['unknown_calls']}/{details['total_calls']})")
    print(f"  业务断链率: {metrics['business_broken_chain_rate']:.2%} ({unknown_breakdown['business_unknown']}/{details['total_calls']})")
    print(f"  可达率: {metrics['reachability_rate']:.2%} ({details['reachable_methods']}/{details['total_methods']})")
    print(f"  关键链路命中率: {metrics['key_chain_hit_rate']:.2%} ({details['matched_key_chains']}/{details['total_key_chains']})")
    print(f"  关键链保留率: {metrics['critical_chain_retention']:.2%}")
    print(f"  关键跳点丢失率: {metrics['critical_hop_dropout']:.2%}")
    print(f"  util unknown 占比: {metrics['util_unknown_ratio']:.2%}")
    print()
    print("补充指标:")
    print(f"  关键链路逐跳命中率: {details['key_chain_hop_hit_rate']:.2%} ({details['matched_key_hops']}/{details['total_key_hops']})")
    print(f"  入口方法数: {details['entry_method_count']}")
    print(f"  内部调用数: {details['internal_calls']}")
    print(f"  外部调用数: {details['external_calls']}")
    print(f"  JDK/标准库 unknown: {unknown_breakdown['jdk_unknown']}")
    print(f"  业务 unknown: {unknown_breakdown['business_unknown']}")
    print()
    print("关键链路详情:")
    for chain in report["critical_chain_results"]:
        status = "PASS" if chain["full_hit"] else "FAIL"
        print(f"  [{status}] {chain['name']} ({chain['matched_hops']}/{chain['total_hops']})")


def save_report(report, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)