import json
import os
import subprocess
import sys
import time
from typing import List, Dict, Tuple

from src.tree.query_service import GraphQueryService


DEFAULT_CRITICAL_CHAINS = [
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


def _normalize_chain_hops(raw_hops):
    """Normalize hop definitions to tuple pairs: [(class, method), ...]."""
    hops = []
    for item in raw_hops or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            cls, method = item[0], item[1]
        elif isinstance(item, dict):
            cls = item.get("class")
            method = item.get("method")
        else:
            continue
        if cls and method:
            hops.append((str(cls), str(method)))
    return hops


def load_critical_chains(config_path=None):
    """Load critical chains from JSON config. Fall back to embedded defaults.

    JSON format:
    {
      "chains": [
        {"name": "flow_name", "hops": [["ClassA", "m1"], ["ClassB", "m2"]]}
      ]
    }
    """
    default_path = os.path.join("config", "critical_chains.json")
    path = config_path or default_path

    if not os.path.exists(path):
        return DEFAULT_CRITICAL_CHAINS, "embedded_default"

    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        raw_chains = payload.get("chains", []) if isinstance(payload, dict) else []
        chains = []
        for chain in raw_chains:
            if not isinstance(chain, dict):
                continue
            name = chain.get("name")
            hops = _normalize_chain_hops(chain.get("hops"))
            if name and len(hops) >= 2:
                chains.append({"name": str(name), "hops": hops})

        if chains:
            return chains, path
        return DEFAULT_CRITICAL_CHAINS, "embedded_default"
    except Exception:
        return DEFAULT_CRITICAL_CHAINS, "embedded_default"


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


def evaluate_critical_chains(query, critical_chains):
    total_chains = len(critical_chains)
    full_hit_chains = 0
    total_hops = 0
    hit_hops = 0
    chain_results = []

    for chain in critical_chains:
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


def suggest_critical_chains(
    chain_count=10,
    max_hops=5,
    entry_limit=80,
    max_per_core_prefix=2,
    core_prefix_len=3,
) -> Dict:
    """Suggest candidate critical chains from the current graph.

    Strategy:
    1) pick top entrypoint candidates from GraphQueryService
    2) for each entry, find one "best" non-unknown path up to max_hops
    3) return top-N chains by path length and signal score
    """
    chain_count = max(1, int(chain_count))
    max_hops = max(2, int(max_hops))
    entry_limit = max(chain_count, int(entry_limit))
    max_per_core_prefix = max(1, int(max_per_core_prefix))
    core_prefix_len = max(1, int(core_prefix_len))

    def _class_score(class_name: str) -> int:
        name = (class_name or "").lower()
        if any(k in name for k in ("controller", "action", "interf")):
            return 1
        if "facade" in name:
            return 3
        if any(k in name for k in ("service", "biz", "bl")):
            return 4
        if any(k in name for k in ("dal", "dao", "repository")):
            return 5
        if any(k in name for k in ("util", "helper", "common")):
            return -2
        return 0

    candidates = []
    with GraphQueryService() as query:
        entries = query.get_entry_methods()[:entry_limit]
        for entry in entries:
            e_class = entry.get("class_name")
            e_method = entry.get("method_name")
            if not e_class or not e_method:
                continue

            hops: List[Tuple[str, str]] = [(e_class, e_method)]
            visited = {(e_class, e_method)}
            curr_class, curr_method = e_class, e_method
            type_score = 0

            for _ in range(max_hops - 1):
                calls = query.get_method_calls(curr_method, curr_class, limit=120)
                valid = []
                for call in calls:
                    callee_class = call.get("callee_class")
                    callee_method = call.get("callee_name")
                    call_type = call.get("call_type")
                    if not callee_class or not callee_method:
                        continue
                    if call_type == "external_unknown":
                        continue
                    key = (callee_class, callee_method)
                    if key in visited:
                        continue

                    score = (3 if call_type == "internal" else 2) + _class_score(callee_class)
                    valid.append((score, callee_class, callee_method, call_type))

                if not valid:
                    break

                valid.sort(key=lambda x: x[0], reverse=True)
                _best_score, next_class, next_method, next_type = valid[0]
                visited.add((next_class, next_method))
                hops.append((next_class, next_method))
                curr_class, curr_method = next_class, next_method
                type_score += 3 if next_type == "internal" else 2

            if len(hops) < 2:
                continue

            chain_name = f"auto_{e_class}_{e_method}".replace(" ", "_")
            candidates.append(
                {
                    "name": chain_name,
                    "hops": hops,
                    "meta": {
                        "entry_class": e_class,
                        "entry_method": e_method,
                        "entry_score": entry.get("entry_score", 0),
                        "node_count": len(hops),
                        "type_score": type_score,
                    },
                }
            )

    # de-duplicate by exact hop sequence
    dedup = {}
    for chain in candidates:
        key = tuple(chain["hops"])
        prev = dedup.get(key)
        if not prev or chain["meta"]["entry_score"] > prev["meta"]["entry_score"]:
            dedup[key] = chain

    ranked = sorted(
        dedup.values(),
        key=lambda c: (
            len(c["hops"]),
            c["meta"].get("type_score", 0),
            c["meta"].get("entry_score", 0),
        ),
        reverse=True,
    )

    # Diversity control: limit candidates sharing the same core path prefix
    # (excluding entry hop) to avoid near-identical suggestions.
    prefix_counts = {}
    final = []
    for chain in ranked:
        core = chain["hops"][1 : 1 + core_prefix_len] if len(chain["hops"]) > 1 else []
        core_key = tuple(core)
        used = prefix_counts.get(core_key, 0)
        if used >= max_per_core_prefix:
            continue

        prefix_counts[core_key] = used + 1
        final.append(chain)
        if len(final) >= chain_count:
            break

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "max_hops": max_hops,
        "entry_limit": entry_limit,
        "max_per_core_prefix": max_per_core_prefix,
        "core_prefix_len": core_prefix_len,
        "generated_count": len(final),
        "chains": [{"name": c["name"], "hops": c["hops"], "meta": c["meta"]} for c in final],
    }


def save_critical_chain_candidates(payload: Dict, output_path: str):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


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


def build_report(max_depth=10, critical_chains_path=None):
    critical_chains, critical_chains_source = load_critical_chains(critical_chains_path)

    with GraphQueryService() as query:
        all_methods = query.get_all_methods()
        call_stats = query.get_call_statistics()
        entry_methods, reachable_methods = collect_reachable_methods(query, max_depth)
        chain_eval = evaluate_critical_chains(query, critical_chains)
        unknown_breakdown = get_unknown_call_breakdown(query)

    total_methods = len(all_methods)
    all_method_keys = {
        (m.get("class_name"), m.get("method_name"))
        for m in all_methods
        if m.get("class_name") and m.get("method_name")
    }
    total_calls = call_stats.get("total", 0)
    unknown_calls = call_stats.get("external_unknown", 0)
    business_unknown = unknown_breakdown["counts"].get("business_unknown", 0)
    unknown_items = unknown_breakdown["items"]

    critical_classes = {
        class_name
        for chain in critical_chains
        for class_name, _ in chain["hops"]
    }
    critical_methods = {
        (class_name, method_name)
        for chain in critical_chains
        for class_name, method_name in chain["hops"]
    }
    critical_reachable_count = len(critical_methods & reachable_methods)
    critical_defined_count = len(critical_methods & all_method_keys)
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
    critical_chain_coverage = (
        critical_reachable_count / len(critical_methods)
        if critical_methods
        else 0.0
    )
    critical_definition_presence = (
        critical_defined_count / len(critical_methods)
        if critical_methods
        else 0.0
    )

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
            "critical_chain_coverage": critical_chain_coverage,
            "critical_definition_presence": critical_definition_presence,
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
            "critical_chain_source": critical_chains_source,
            "configured_critical_chain_count": len(critical_chains),
            "critical_method_count": len(critical_methods),
            "defined_critical_method_count": critical_defined_count,
            "reachable_critical_method_count": critical_reachable_count,
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
    print(f"  关键链定义命中率: {metrics['critical_definition_presence']:.2%} ({details['defined_critical_method_count']}/{details['critical_method_count']})")
    print(f"  关键链覆盖率: {metrics['critical_chain_coverage']:.2%} ({details['reachable_critical_method_count']}/{details['critical_method_count']})")
    print(f"  关键链保留率: {metrics['critical_chain_retention']:.2%}")
    print(f"  关键跳点丢失率: {metrics['critical_hop_dropout']:.2%}")
    print(f"  util unknown 占比: {metrics['util_unknown_ratio']:.2%}")
    print()
    print("补充指标:")
    print(f"  关键链路逐跳命中率: {details['key_chain_hop_hit_rate']:.2%} ({details['matched_key_hops']}/{details['total_key_hops']})")
    print(f"  关键链配置来源: {details['critical_chain_source']}")
    print(f"  配置关键链数量: {details['configured_critical_chain_count']}")
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