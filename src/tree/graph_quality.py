import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from typing import List, Dict, Tuple

from src.config import Config
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

UNKNOWN_CATEGORIES = [
    "jdk_core",
    "infra_framework",
    "third_party_lib",
    "internal_shared_lib_missing",
    "true_unresolved",
]

INFRA_FRAMEWORK_MARKERS = (
    "logger",
    "log",
    "transaction",
    "tx",
    "sqlsession",
    "mapper",
    "jdbc",
    "hibernate",
    "mybatis",
    "spring",
    "cache",
    "redis",
    "mq",
    "kafka",
    "resttemplate",
    "entitymanager",
)

THIRD_PARTY_MARKERS = (
    "fastjson",
    "jackson",
    "gson",
    "guava",
    "hutool",
    "apache",
    "commons",
    "okhttp",
    "poi",
    "lombok",
)

INTERNAL_SHARED_HINTS = (
    "dto",
    "vo",
    "dao",
    "service",
    "facade",
    "action",
    "util",
    "helper",
    "manager",
    "client",
)


def _classify_unknown_method_actionable(row):
    rel_category = (row.get("rel_unknown_category") or "").strip().lower()
    node_category = (row.get("node_unknown_category") or "").strip().lower()
    raw_category = rel_category or node_category
    callee_name = (row.get("callee_name") or "").strip().lower()
    caller_class = (row.get("caller_class") or "").strip().lower()

    if raw_category in UNKNOWN_CATEGORIES:
        return raw_category
    if raw_category == "jdk_unknown":
        return "jdk_core"

    if callee_name in JDK_LIKELY_METHODS:
        return "jdk_core"
    if any(token in callee_name for token in INFRA_FRAMEWORK_MARKERS):
        return "infra_framework"
    if any(token in callee_name for token in THIRD_PARTY_MARKERS):
        return "third_party_lib"
    if any(token in callee_name for token in INTERNAL_SHARED_HINTS):
        return "internal_shared_lib_missing"
    if any(token in caller_class for token in ("common", "shared", "base")):
        return "internal_shared_lib_missing"
    return "true_unresolved"


def _build_unknown_top_callers(classified_rows, top_n=15):
    total = len(classified_rows)
    counter = Counter()
    category_counter = Counter()

    for row in classified_rows:
        key = (row.get("caller_class") or "", row.get("caller_name") or "")
        counter[key] += 1
        category_counter[(key, row.get("category") or "true_unresolved")] += 1

    top = []
    for (caller_class, caller_name), count in counter.most_common(top_n):
        main_category = None
        main_category_count = 0
        for category in UNKNOWN_CATEGORIES:
            c = category_counter.get(((caller_class, caller_name), category), 0)
            if c > main_category_count:
                main_category_count = c
                main_category = category

        top.append(
            {
                "caller_class": caller_class,
                "caller_name": caller_name,
                "count": count,
                "ratio": (count / total) if total else 0.0,
                "dominant_category": main_category or "true_unresolved",
            }
        )
    return top


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


def summarize_entry_rule_hits(entry_methods):
    rule_counts = Counter()
    confidence_counts = Counter()

    for item in entry_methods:
        confidence = item.get("entry_confidence") or "low"
        confidence_counts[confidence] += 1

        for trace in item.get("entry_rule_trace") or []:
            rule = trace.get("rule")
            if rule:
                rule_counts[rule] += 1

    top_rules = [
        {"rule": rule, "hits": count}
        for rule, count in rule_counts.most_common(10)
    ]

    total_entries = len(entry_methods)
    high_entries = confidence_counts.get("high", 0)

    return {
        "total_entries": total_entries,
        "confidence_counts": dict(confidence_counts),
        "top_rules": top_rules,
        "entry_confidence_proxy": (high_entries / total_entries) if total_entries else 0.0,
    }


def evaluate_critical_chains(query, critical_chains, all_method_keys=None):
    total_chains = len(critical_chains)
    full_hit_chains = 0
    total_hops = 0
    hit_hops = 0
    chain_results = []
    all_method_keys = all_method_keys or set()

    for chain in critical_chains:
        hop_results = []
        is_full_hit = True
        first_break = None

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
                if first_break is None:
                    source_defined = source in all_method_keys
                    target_defined = target in all_method_keys
                    first_break = {
                        "break_hop_index": len(hop_results) + 1,
                        "from": {"class": source[0], "method": source[1]},
                        "to": {"class": target[0], "method": target[1]},
                        "reason": (
                            "missing_method_definition"
                            if not source_defined or not target_defined
                            else "missing_call"
                        ),
                    }

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
                "first_break": first_break,
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


def _coarse_layer_bucket(file_path, class_name):
    path = (file_path or "").lower().replace("\\", "/")
    cls = (class_name or "").lower()

    if any(token in path for token in ("/controller/", "/action/", "/interf/", "/interface/", "/api/", "/web/", "/ui/")):
        return "ui"
    if any(token in path for token in ("/dal/", "/dao/", "/repository/", "/db/", "/mapper/")):
        return "db"
    if any(token in path for token in ("/service/", "/biz/", "/bl/", "/facade/")):
        return "bl"

    if cls.endswith(("action", "controller", "interf", "api")):
        return "ui"
    if cls.endswith(("dao", "repository", "mapper")) or cls.startswith("db"):
        return "db"
    if cls.endswith(("service", "biz", "facade")) or cls.startswith("bl"):
        return "bl"

    return "other"


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
    counts = {key: 0 for key in UNKNOWN_CATEGORIES}

    for row in rows:
        category = _classify_unknown_method_actionable(row)
        counts[category] += 1
        row["category"] = category
        classified_rows.append(row)

    counts["total_unknown"] = len(classified_rows)
    counts["jdk_unknown"] = counts["jdk_core"]
    counts["business_unknown"] = counts["total_unknown"] - counts["jdk_core"]

    top_callers = _build_unknown_top_callers(classified_rows, top_n=15)
    return {"counts": counts, "items": classified_rows, "top_callers": top_callers}


def get_graph_integrity_stats(query):
    with query.driver.session() as session:
        result = session.run(
            """
            MATCH (m:Method)
            OPTIONAL MATCH (m)-[o:CALLS]->()
            OPTIONAL MATCH ()-[i:CALLS]->(m)
            WITH m, count(DISTINCT o) AS out_degree, count(DISTINCT i) AS in_degree
            RETURN count(m) AS method_count,
                   count(CASE WHEN out_degree = 0 AND in_degree = 0 THEN 1 END) AS isolated_method_count
            """
        )
        row = result.single()
    return {
        "method_count": int(row["method_count"] or 0) if row else 0,
        "isolated_method_count": int(row["isolated_method_count"] or 0) if row else 0,
    }


def get_structural_risk_stats(query):
    forbidden_pairs = {("ui", "db"), ("db", "bl"), ("bl", "ui")}

    with query.driver.session() as session:
        violation_result = session.run(
            """
            MATCH (caller:Method)-[:CALLS]->(callee:Method)
            RETURN caller.file_path AS caller_path,
                   caller.class_name AS caller_class,
                   callee.file_path AS callee_path,
                   callee.class_name AS callee_class,
                   count(*) AS edge_count
            ORDER BY edge_count DESC
            """
        )
        violation_rows = [dict(record) for record in violation_result]

        cycle_result = session.run(
            """
            MATCH (c1:Class)<-[:BELONGS_TO]-(:Method)-[:CALLS]->(:Method)-[:BELONGS_TO]->(c2:Class)
            WHERE c1.name < c2.name
            WITH c1, c2,
                 size([(c1)<-[:BELONGS_TO]-(:Method)-[:CALLS]->(:Method)-[:BELONGS_TO]->(c2) | 1]) AS forward_count,
                 size([(c2)<-[:BELONGS_TO]-(:Method)-[:CALLS]->(:Method)-[:BELONGS_TO]->(c1) | 1]) AS reverse_count
            WHERE forward_count > 0 AND reverse_count > 0
            RETURN c1.name AS class_a,
                   c2.name AS class_b,
                   forward_count,
                   reverse_count,
                   forward_count + reverse_count AS total_edges
            ORDER BY total_edges DESC
            """
        )
        cycle_rows = [dict(record) for record in cycle_result]

        god_result = session.run(
            """
            MATCH (m:Method)
            OPTIONAL MATCH (m)-[r:CALLS]->()
            WITH m, count(r) AS out_degree
            RETURN count(m) AS method_count,
                   count(CASE WHEN out_degree > 100 THEN 1 END) AS god_method_count
            """
        )
        god_row = god_result.single()

        hotspot_result = session.run(
            """
            MATCH ()-[r:CALLS]->(m:Method)
            WITH m, count(r) AS in_degree
            ORDER BY in_degree DESC
            WITH collect(in_degree) AS degrees
            RETURN reduce(total = 0, d IN degrees | total + d) AS total_in_degree,
                   reduce(top = 0, d IN degrees[0..20] | top + d) AS top20_in_degree
            """
        )
        hotspot_row = hotspot_result.single()

    total_edges = 0
    violation_edges = 0
    top_violations = []
    for row in violation_rows:
        edge_count = int(row.get("edge_count") or 0)
        total_edges += edge_count
        src_layer = _coarse_layer_bucket(row.get("caller_path"), row.get("caller_class"))
        dst_layer = _coarse_layer_bucket(row.get("callee_path"), row.get("callee_class"))
        if (src_layer, dst_layer) not in forbidden_pairs:
            continue
        violation_edges += edge_count
        top_violations.append(
            {
                "caller_class": row.get("caller_class"),
                "callee_class": row.get("callee_class"),
                "caller_layer": src_layer,
                "callee_layer": dst_layer,
                "edge_count": edge_count,
            }
        )

    method_count = int(god_row["method_count"] or 0) if god_row else 0
    god_method_count = int(god_row["god_method_count"] or 0) if god_row else 0
    total_in_degree = int(hotspot_row["total_in_degree"] or 0) if hotspot_row else 0
    top20_in_degree = int(hotspot_row["top20_in_degree"] or 0) if hotspot_row else 0

    return {
        "layer_violation_rate": (violation_edges / total_edges) if total_edges else 0.0,
        "layer_violation_edges": violation_edges,
        "top_layer_violations": sorted(top_violations, key=lambda x: x["edge_count"], reverse=True)[:10],
        "cycle_count": len(cycle_rows),
        "top_cycle_modules": cycle_rows[:10],
        "god_method_ratio": (god_method_count / method_count) if method_count else 0.0,
        "god_method_count": god_method_count,
        "hotspot_fragility_top20_share": (top20_in_degree / total_in_degree) if total_in_degree else 0.0,
        "top20_in_degree": top20_in_degree,
        "total_in_degree": total_in_degree,
    }


def build_report(max_depth=10, critical_chains_path=None):
    run_id = f"gq-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    critical_chains, critical_chains_source = load_critical_chains(critical_chains_path)

    with GraphQueryService() as query:
        all_methods = query.get_all_methods()
        all_method_keys = {
            (m.get("class_name"), m.get("method_name"))
            for m in all_methods
            if m.get("class_name") and m.get("method_name")
        }
        all_classes = query.get_all_classes()
        call_stats = query.get_call_statistics()
        entry_methods, reachable_methods = collect_reachable_methods(query, max_depth)
        chain_eval = evaluate_critical_chains(query, critical_chains, all_method_keys)
        unknown_breakdown = get_unknown_call_breakdown(query)
        entry_rule_stats = summarize_entry_rule_hits(entry_methods)
        integrity = get_graph_integrity_stats(query)
        structural_risks = get_structural_risk_stats(query)

    total_methods = len(all_methods)
    total_calls = call_stats.get("total", 0)
    unknown_calls = call_stats.get("external_unknown", 0)
    business_unknown = unknown_breakdown["counts"].get("business_unknown", 0)
    unknown_items = unknown_breakdown["items"]
    unknown_top_callers = unknown_breakdown.get("top_callers", [])

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
    critical_chain_reach_share = (
        len(critical_methods) / len(reachable_methods)
        if reachable_methods
        else 0.0
    )
    critical_definition_presence = (
        critical_defined_count / len(critical_methods)
        if critical_methods
        else 0.0
    )
    isolated_method_ratio = (
        integrity["isolated_method_count"] / total_methods
        if total_methods
        else 0.0
    )

    return {
        "run_id": run_id,
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
            "critical_chain_reach_share": critical_chain_reach_share,
            "critical_definition_presence": critical_definition_presence,
            "entry_confidence_proxy": entry_rule_stats["entry_confidence_proxy"],
            "layer_violation_rate": structural_risks["layer_violation_rate"],
            "cycle_count": structural_risks["cycle_count"],
            "god_method_ratio": structural_risks["god_method_ratio"],
            "isolated_method_ratio": isolated_method_ratio,
            "hotspot_fragility_top20_share": structural_risks["hotspot_fragility_top20_share"],
        },
        "details": {
            "project_path": os.path.abspath(Config.PROJECT_PATH),
            "snapshot_ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dedup_rule_version": "v1",
            "query_max_depth": int(max_depth),
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
            "unknown_top_callers": unknown_top_callers,
            "entry_rule_stats": entry_rule_stats,
            "integrity_checks": {
                "method_count": integrity["method_count"],
                "class_count": len(all_classes),
                "call_edge_count": total_calls,
                "isolated_method_count": integrity["isolated_method_count"],
            },
            "structural_risks": structural_risks,
            "coverage_metric_note": (
                "critical_chain_coverage = reachable_critical_methods / critical_methods, "
                "critical_chain_reach_share = critical_methods / reachable_methods"
            ),
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
    print(f"run_id: {report.get('run_id', '-')}")
    print(f"时间: {report['timestamp']}")
    print()
    print("核心指标:")
    print(f"  断链率: {metrics['broken_chain_rate']:.2%} ({details['unknown_calls']}/{details['total_calls']})")
    print(f"  业务断链率: {metrics['business_broken_chain_rate']:.2%} ({unknown_breakdown['business_unknown']}/{details['total_calls']})")
    print(f"  可达率: {metrics['reachability_rate']:.2%} ({details['reachable_methods']}/{details['total_methods']})")
    print(f"  关键链路命中率: {metrics['key_chain_hit_rate']:.2%} ({details['matched_key_chains']}/{details['total_key_chains']})")
    print(f"  关键链定义命中率: {metrics['critical_definition_presence']:.2%} ({details['defined_critical_method_count']}/{details['critical_method_count']})")
    print(f"  关键链覆盖率: {metrics['critical_chain_coverage']:.2%} ({details['reachable_critical_method_count']}/{details['critical_method_count']})")
    print(f"  关键链可达占比: {metrics['critical_chain_reach_share']:.2%} ({details['critical_method_count']}/{details['reachable_methods']})")
    print(f"  关键链保留率: {metrics['critical_chain_retention']:.2%}")
    print(f"  关键跳点丢失率: {metrics['critical_hop_dropout']:.2%}")
    print(f"  入口识别置信代理: {metrics['entry_confidence_proxy']:.2%}")
    print(f"  分层违规率: {metrics['layer_violation_rate']:.2%}")
    print(f"  God method 比例: {metrics['god_method_ratio']:.2%}")
    print(f"  孤立方法比例: {metrics['isolated_method_ratio']:.2%}")
    print(f"  热点脆弱度 Top20 占比: {metrics['hotspot_fragility_top20_share']:.2%}")
    print(f"  util unknown 占比: {metrics['util_unknown_ratio']:.2%}")
    print()
    print("补充指标:")
    print(f"  关键链路逐跳命中率: {details['key_chain_hop_hit_rate']:.2%} ({details['matched_key_hops']}/{details['total_key_hops']})")
    print(f"  关键链配置来源: {details['critical_chain_source']}")
    print(f"  配置关键链数量: {details['configured_critical_chain_count']}")
    print(f"  入口方法数: {details['entry_method_count']}")
    print(f"  内部调用数: {details['internal_calls']}")
    print(f"  外部调用数: {details['external_calls']}")
    print(f"  JDK/标准库 unknown(兼容): {unknown_breakdown['jdk_unknown']}")
    print(f"  业务 unknown(兼容): {unknown_breakdown['business_unknown']}")
    print("  unknown 可行动分类:")
    print(f"    - jdk_core: {unknown_breakdown.get('jdk_core', 0)}")
    print(f"    - infra_framework: {unknown_breakdown.get('infra_framework', 0)}")
    print(f"    - third_party_lib: {unknown_breakdown.get('third_party_lib', 0)}")
    print(f"    - internal_shared_lib_missing: {unknown_breakdown.get('internal_shared_lib_missing', 0)}")
    print(f"    - true_unresolved: {unknown_breakdown.get('true_unresolved', 0)}")

    integrity = details.get("integrity_checks", {})
    structural_risks = details.get("structural_risks", {})
    print("  数据完整性校验:")
    print(f"    - 方法节点数: {integrity.get('method_count', 0)}")
    print(f"    - 类节点数: {integrity.get('class_count', 0)}")
    print(f"    - CALLS 边数: {integrity.get('call_edge_count', 0)}")
    print(f"    - 孤立方法数: {integrity.get('isolated_method_count', 0)}")

    entry_rule_stats = details.get("entry_rule_stats", {})
    top_rules = entry_rule_stats.get("top_rules", [])
    if top_rules:
        print("  入口规则命中 Top:")
        for item in top_rules[:5]:
            print(f"    - {item.get('rule')}: {item.get('hits')} hits")

    top_unknown_callers = details.get("unknown_top_callers", [])
    if top_unknown_callers:
        print("  unknown Top 调用点:")
        for item in top_unknown_callers[:5]:
            print(
                f"    - {item.get('caller_class')}.{item.get('caller_name')}: "
                f"{item.get('count')} ({item.get('ratio', 0.0):.2%}), "
                f"dominant={item.get('dominant_category')}"
            )

    print(f"  循环依赖数: {metrics['cycle_count']}")
    top_cycles = structural_risks.get("top_cycle_modules", [])
    if top_cycles:
        print("  循环依赖 Top 模块:")
        for item in top_cycles[:5]:
            print(
                f"    - {item.get('class_a')} <-> {item.get('class_b')}: "
                f"{item.get('total_edges')}"
            )

    top_violations = structural_risks.get("top_layer_violations", [])
    if top_violations:
        print("  分层违规 Top 边:")
        for item in top_violations[:5]:
            print(
                f"    - {item.get('caller_class')}({item.get('caller_layer')}) -> "
                f"{item.get('callee_class')}({item.get('callee_layer')}): "
                f"{item.get('edge_count')}"
            )
    print()
    print("关键链路详情:")
    for chain in report["critical_chain_results"]:
        status = "PASS" if chain["full_hit"] else "FAIL"
        print(f"  [{status}] {chain['name']} ({chain['matched_hops']}/{chain['total_hops']})")
        if not chain["full_hit"] and chain.get("first_break"):
            first_break = chain["first_break"]
            print(
                "    first_break: "
                f"hop#{first_break['break_hop_index']} "
                f"{first_break['from']['class']}.{first_break['from']['method']} -> "
                f"{first_break['to']['class']}.{first_break['to']['method']} "
                f"({first_break['reason']})"
            )


def save_report(report, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)