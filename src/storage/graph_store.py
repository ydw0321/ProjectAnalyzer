from neo4j import GraphDatabase
from src.config import Config
from tqdm import tqdm


JDK_LIKELY_METHODS = {
    "abs", "add", "before", "compareTo", "contains", "currentTimeMillis", "divide",
    "endsWith", "equals", "filter", "findFirst", "format", "getMessage", "getStackTrace",
    "getTime", "isEmpty", "iterator", "length", "multiply", "nanoTime", "now", "orElse",
    "randomUUID", "remove", "setScale", "size", "split", "startsWith", "stream", "substring",
    "subtract", "toString", "trim", "valueOf",
}


class GraphStore:
    def __init__(self, uri=None, user=None, password=None):
        uri = uri or Config.NEO4J_URI
        user = user or Config.NEO4J_USER
        password = password or Config.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            session.run("RETURN 1")
        self._ensure_indexes()

    def _ensure_indexes(self):
        """确保核心查询路径有索引，避免大规模 MATCH/MERGE 退化为全表扫描。"""
        index_statements = [
            "CREATE INDEX method_class_name_idx IF NOT EXISTS FOR (m:Method) ON (m.class_name, m.name)",
            "CREATE INDEX method_class_name_param_idx IF NOT EXISTS FOR (m:Method) ON (m.class_name, m.name, m.param_count)",
            "CREATE INDEX class_name_file_idx IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)",
            "CREATE INDEX external_method_name_idx IF NOT EXISTS FOR (e:ExternalMethod) ON (e.name)",
        ]
        with self.driver.session() as session:
            for stmt in index_statements:
                session.run(stmt)

    @staticmethod
    def _chunk_rows(rows, batch_size):
        for i in range(0, len(rows), batch_size):
            yield rows[i:i + batch_size]

    @staticmethod
    def _dedupe_rows(rows, key_fields):
        seen = set()
        unique_rows = []
        for row in rows:
            key = tuple(row.get(field) for field in key_fields)
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)
        return unique_rows

    def _run_chunked_query(self, session, query, rows, batch_size, progress=None, stage_label=None):
        for chunk in self._chunk_rows(rows, batch_size):
            session.run(query, rows=chunk)
            if progress is not None:
                progress.update(len(chunk))
                if stage_label:
                    progress.set_postfix_str(stage_label)

    def add_class_node(self, class_name, file_path):
        """创建类节点"""
        with self.driver.session() as session:
            session.run(
                "MERGE (c:Class {name: $name, file_path: $file_path})",
                name=class_name,
                file_path=file_path,
            )

    def batch_add_class_nodes(self, class_nodes):
        """批量创建类节点"""
        if not class_nodes:
            return
        class_nodes = self._dedupe_rows(class_nodes, ["name", "file_path"])
        batch_size = max(1, Config.NEO4J_WRITE_BATCH_SIZE)
        with self.driver.session() as session:
            with tqdm(total=len(class_nodes), desc="写入 Neo4j Class 节点", unit="row", leave=True) as progress:
                self._run_chunked_query(
                    session,
                    """
                    UNWIND $rows AS row
                    MERGE (c:Class {name: row.name, file_path: row.file_path})
                    """,
                    class_nodes,
                    batch_size,
                    progress=progress,
                    stage_label="class-nodes",
                )

    def add_method_node(self, name, class_name, file_path, param_count=0):
        """创建方法节点"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (m:Method {name: $name, class_name: $class_name})
                SET m.file_path = $file_path,
                    m.param_count = $param_count
                """,
                name=name,
                class_name=class_name,
                file_path=file_path,
                param_count=param_count,
            )

    def clear_graph(self):
        """清空当前 Neo4j 图数据（仅删除节点和关系，不修改数据库配置）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def _classify_unknown_method(self, method_name: str) -> str:
        if method_name in JDK_LIKELY_METHODS:
            return "jdk_unknown"
        return "business_unknown"

    def batch_add_method_nodes(self, method_nodes):
        """批量创建方法节点"""
        if not method_nodes:
            return
        method_nodes = self._dedupe_rows(method_nodes, ["name", "class_name", "file_path", "param_count"])
        batch_size = max(1, Config.NEO4J_WRITE_BATCH_SIZE)
        with self.driver.session() as session:
            with tqdm(total=len(method_nodes), desc="写入 Neo4j Method 节点", unit="row", leave=True) as progress:
                self._run_chunked_query(
                    session,
                    """
                    UNWIND $rows AS row
                    MERGE (m:Method {name: row.name, class_name: row.class_name})
                    SET m.file_path = row.file_path,
                        m.param_count = row.param_count
                    """,
                    method_nodes,
                    batch_size,
                    progress=progress,
                    stage_label="method-nodes",
                )

    def add_call_relationship(self, caller, callee, caller_class=None, callee_class=None, call_type="internal"):
        """创建方法调用关系（支持跨类调用）"""
        with self.driver.session() as session:
            if call_type == "external":
                if caller_class and callee_class and callee_class != "Unknown":
                    session.run(
                        """
                        MATCH (caller:Method {name: $caller, class_name: $caller_class})
                        OPTIONAL MATCH (callee:Method {name: $callee, class_name: $callee_class})
                        FOREACH (_ IN CASE WHEN callee IS NOT NULL THEN [1] ELSE [] END |
                            MERGE (caller)-[:CALLS {via_field: $via_field, type: 'external'}]->(callee)
                        )
                        FOREACH (_ IN CASE WHEN callee IS NULL THEN [1] ELSE [] END |
                            MERGE (caller)-[:CALLS {type: 'external_unknown'}]->(:ExternalMethod {name: $callee})
                        )
                        """,
                        caller=caller,
                        caller_class=caller_class,
                        callee=callee,
                        callee_class=callee_class,
                        via_field=caller + "_to_" + callee,
                    )
                else:
                    session.run(
                        """
                        MATCH (caller:Method {name: $caller, class_name: $caller_class})
                        MERGE (caller)-[:CALLS {type: 'external_unknown'}]->(callee:ExternalMethod {name: $callee})
                        """,
                        caller=caller,
                        caller_class=caller_class,
                        callee=callee,
                    )
            else:
                if not caller_class:
                    return
                target_class = callee_class or caller_class
                session.run(
                    """
                    MATCH (caller:Method {name: $caller, class_name: $caller_class})
                    MATCH (callee:Method {name: $callee, class_name: $target_class})
                    MERGE (caller)-[:CALLS {type: 'internal'}]->(callee)
                    """,
                    caller=caller,
                    caller_class=caller_class,
                    callee=callee,
                    target_class=target_class,
                )

    def _build_signature_index(self, signature_index=None):
        """构建 (class_name, method_name) -> {param_count...} 索引。"""
        if signature_index is not None:
            normalized = {}
            for key, values in signature_index.items():
                if not isinstance(key, tuple) or len(key) != 2:
                    continue
                class_name, method_name = key
                if not class_name or not method_name:
                    continue
                if isinstance(values, (set, list, tuple)):
                    candidate_values = values
                else:
                    candidate_values = [values]
                normalized[(class_name, method_name)] = {
                    int(v) if v is not None else 0 for v in candidate_values
                }
            return normalized

        index = {}
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Method)
                RETURN m.class_name AS class_name, m.name AS method_name, m.param_count AS param_count
                """
            )
            for row in result:
                key = (row["class_name"], row["method_name"])
                index.setdefault(key, set()).add(row.get("param_count", 0))
        return index

    def batch_add_call_relationships(self, calls, signature_index=None):
        """批量创建方法调用关系，并返回匹配观测统计"""
        stats = {
            "total_rows": 0,
            "deduplicated_rows": 0,
            "internal_rows": 0,
            "external_rows": 0,
            "direct_unknown_rows": 0,
            "signature_exact_hits": 0,
            "unique_fallback_hits": 0,
            "tolerant_hits": 0,
            "unmatched_to_unknown": 0,
            "internal_unmatched_dropped": 0,
        }
        if not calls:
            return stats

        internal_rows = []
        external_rows = []
        unknown_rows = []

        for call in calls:
            call_type = call.get("type", "internal")
            unknown_category = call.get("unknown_category") or self._classify_unknown_method(call.get("callee", ""))
            row = {
                "caller": call.get("caller"),
                "callee": call.get("callee"),
                "caller_class": call.get("caller_class"),
                "callee_class": call.get("callee_class"),
                "arg_count": call.get("arg_count", 0),
                "type": call_type,
                "unknown_category": unknown_category,
                "via_field": f"{call.get('caller', '')}_to_{call.get('callee', '')}",
            }

            if not row["caller"] or not row["callee"]:
                continue
            if not row["caller_class"]:
                continue

            if call_type == "external":
                if row["callee_class"] and row["callee_class"] != "Unknown":
                    external_rows.append(row)
                else:
                    unknown_rows.append(row)
            else:
                row["target_class"] = row["callee_class"] or row["caller_class"]
                internal_rows.append(row)

        stats["total_rows"] = len(internal_rows) + len(external_rows) + len(unknown_rows)
        stats["internal_rows"] = len(internal_rows)
        stats["external_rows"] = len(external_rows)
        stats["direct_unknown_rows"] = len(unknown_rows)

        internal_rows = self._dedupe_rows(
            internal_rows,
            ["caller", "caller_class", "callee", "target_class", "arg_count", "type"],
        )
        external_rows = self._dedupe_rows(
            external_rows,
            ["caller", "caller_class", "callee", "callee_class", "arg_count", "type", "via_field"],
        )
        unknown_rows = self._dedupe_rows(
            unknown_rows,
            ["caller", "caller_class", "callee", "arg_count", "unknown_category", "type"],
        )
        stats["deduplicated_rows"] = len(internal_rows) + len(external_rows) + len(unknown_rows)

        signature_index = self._build_signature_index(signature_index=signature_index)

        def select_mode(class_name, method_name, arg_count):
            """返回 (mode, best_param_count_or_None)。
            mode 取值: 'exact' | 'fallback' | 'tolerant' | 'none'
            best_param_count: tolerant 模式下最近候选参数数，其余为 None。
            """
            candidates = signature_index.get((class_name, method_name), set())
            if not candidates:
                return "none", None
            if Config.USE_SIGNATURE_MATCH:
                if arg_count in candidates:
                    return "exact", arg_count
                if len(candidates) == 1:
                    return "fallback", None
                if Config.SIGNATURE_MATCH_TOLERANT:
                    closest = min(candidates, key=lambda c: abs(arg_count - c))
                    if abs(arg_count - closest) <= Config.SIGNATURE_TOLERANT_MAX_DIFF:
                        return "tolerant", closest
                return "none", None
            else:
                return "fallback", None

        internal_exact_rows = []
        internal_fallback_rows = []
        internal_tolerant_rows = []
        for row in internal_rows:
            mode, best_pc = select_mode(row["target_class"], row["callee"], row["arg_count"])
            if mode == "exact":
                internal_exact_rows.append(row)
                stats["signature_exact_hits"] += 1
            elif mode == "fallback":
                internal_fallback_rows.append(row)
                stats["unique_fallback_hits"] += 1
            elif mode == "tolerant":
                r = dict(row)
                r["best_param_count"] = best_pc
                internal_tolerant_rows.append(r)
                stats["tolerant_hits"] += 1
            else:
                stats["internal_unmatched_dropped"] += 1

        external_exact_rows = []
        external_fallback_rows = []
        external_tolerant_rows = []
        external_unmatched_rows = []
        for row in external_rows:
            mode, best_pc = select_mode(row["callee_class"], row["callee"], row["arg_count"])
            if mode == "exact":
                external_exact_rows.append(row)
                stats["signature_exact_hits"] += 1
            elif mode == "fallback":
                external_fallback_rows.append(row)
                stats["unique_fallback_hits"] += 1
            elif mode == "tolerant":
                r = dict(row)
                r["best_param_count"] = best_pc
                external_tolerant_rows.append(r)
                stats["tolerant_hits"] += 1
            else:
                external_unmatched_rows.append(row)

        if external_unmatched_rows:
            stats["unmatched_to_unknown"] = len(external_unmatched_rows)
            unknown_rows.extend(external_unmatched_rows)
            unknown_rows = self._dedupe_rows(
                unknown_rows,
                ["caller", "caller_class", "callee", "arg_count", "unknown_category", "type"],
            )

        batch_size = max(1, Config.NEO4J_WRITE_BATCH_SIZE)
        total_write_rows = (
            len(internal_exact_rows)
            + len(internal_fallback_rows)
            + len(internal_tolerant_rows)
            + len(external_exact_rows)
            + len(external_fallback_rows)
            + len(external_tolerant_rows)
            + len(unknown_rows)
        )

        with self.driver.session() as session:
            with tqdm(
                total=total_write_rows,
                desc="写入 Neo4j 调用关系",
                unit="row",
                leave=True,
            ) as progress:
                if internal_exact_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.target_class, param_count: row.arg_count})
                        MERGE (caller)-[r:CALLS {type: 'internal'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'exact'
                        """,
                        internal_exact_rows,
                        batch_size,
                        progress=progress,
                        stage_label="internal-exact",
                    )

                if internal_fallback_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.target_class})
                        MERGE (caller)-[r:CALLS {type: 'internal'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'fallback'
                        """,
                        internal_fallback_rows,
                        batch_size,
                        progress=progress,
                        stage_label="internal-fallback",
                    )

                if external_exact_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.callee_class, param_count: row.arg_count})
                        MERGE (caller)-[r:CALLS {via_field: row.via_field, type: 'external'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'exact'
                        """,
                        external_exact_rows,
                        batch_size,
                        progress=progress,
                        stage_label="external-exact",
                    )

                if external_fallback_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.callee_class})
                        MERGE (caller)-[r:CALLS {via_field: row.via_field, type: 'external'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'fallback'
                        """,
                        external_fallback_rows,
                        batch_size,
                        progress=progress,
                        stage_label="external-fallback",
                    )

                if internal_tolerant_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.target_class, param_count: row.best_param_count})
                        MERGE (caller)-[r:CALLS {type: 'internal'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'tolerant'
                        """,
                        internal_tolerant_rows,
                        batch_size,
                        progress=progress,
                        stage_label="internal-tolerant",
                    )

                if external_tolerant_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MATCH (callee:Method {name: row.callee, class_name: row.callee_class, param_count: row.best_param_count})
                        MERGE (caller)-[r:CALLS {via_field: row.via_field, type: 'external'}]->(callee)
                        SET r.arg_count = row.arg_count, r.match_mode = 'tolerant'
                        """,
                        external_tolerant_rows,
                        batch_size,
                        progress=progress,
                        stage_label="external-tolerant",
                    )

                if unknown_rows:
                    self._run_chunked_query(
                        session,
                        """
                        UNWIND $rows AS row
                        MATCH (caller:Method {name: row.caller, class_name: row.caller_class})
                        MERGE (callee:ExternalMethod {name: row.callee})
                        SET callee.category = coalesce(callee.category, row.unknown_category)
                        MERGE (caller)-[r:CALLS {type: 'external_unknown'}]->(callee)
                        SET r.arg_count = row.arg_count, r.unknown_category = row.unknown_category
                        """,
                        unknown_rows,
                        batch_size,
                        progress=progress,
                        stage_label="external-unknown",
                    )

        return stats

    def add_belongs_to_relationship(self, method_name, class_name, file_path=None, param_count=0):
        """创建方法属于类的关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (m:Method {name: $method_name, class_name: $class_name, param_count: $param_count})
                MATCH (c:Class {name: $class_name, file_path: $file_path})
                MERGE (m)-[:BELONGS_TO]->(c)
                """,
                method_name=method_name,
                class_name=class_name,
                file_path=file_path,
                param_count=param_count,
            )

    def batch_add_belongs_to_relationships(self, method_class_pairs):
        """批量创建 BELONGS_TO 关系"""
        if not method_class_pairs:
            return
        method_class_pairs = self._dedupe_rows(
            method_class_pairs,
            ["method_name", "class_name", "file_path", "param_count"],
        )
        batch_size = max(1, Config.NEO4J_WRITE_BATCH_SIZE)
        with self.driver.session() as session:
            with tqdm(total=len(method_class_pairs), desc="写入 Neo4j BELONGS_TO", unit="row", leave=True) as progress:
                self._run_chunked_query(
                    session,
                    """
                    UNWIND $rows AS row
                    MATCH (m:Method {name: row.method_name, class_name: row.class_name, param_count: row.param_count})
                    MATCH (c:Class {name: row.class_name, file_path: row.file_path})
                    MERGE (m)-[:BELONGS_TO]->(c)
                    """,
                    method_class_pairs,
                    batch_size,
                    progress=progress,
                    stage_label="belongs-to",
                )

    def resolve_external_unknown_calls(self):
        """将可唯一匹配的 external_unknown 调用补链到 Method 节点，再用启发式多候选补链"""
        with self.driver.session() as session:
            # Pass 1: 唯一名称精确补链
            result = session.run(
                """
                MATCH (caller:Method)-[r:CALLS {type: 'external_unknown'}]->(ext:ExternalMethod)
                WITH caller, r, ext
                MATCH (candidate:Method {name: ext.name})
                WITH caller, r, ext, collect(candidate) AS candidates
                WHERE size(candidates) = 1
                WITH caller, r, ext, candidates[0] AS target
                MERGE (caller)-[c:CALLS {type: 'external', inferred: true}]->(target)
                SET c.inferred_reason = 'unique_name', c.confidence = 1.0
                DELETE r
                RETURN count(*) AS resolved
                """
            )
            resolved_p1 = result.single()["resolved"]

        # Pass 2: 路径邻近度启发式多候选补链
        resolved_p2 = self._resolve_by_heuristics()

        with self.driver.session() as session:
            session.run(
                """
                MATCH (ext:ExternalMethod)
                WHERE NOT (()-[:CALLS]->(ext))
                DELETE ext
                """
            )

        return resolved_p1 + resolved_p2

    def _resolve_by_heuristics(self) -> int:
        """对剩余多候选 external_unknown 调用用文件路径邻近度启发式补链。
        仅当 caller 与 candidate 有至少 1 层公共路径前缀时才补链，
        记录 inferred_reason 与 confidence 属性。
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (caller:Method)-[:CALLS {type: 'external_unknown'}]->(ext:ExternalMethod)
                WITH caller, ext
                MATCH (candidate:Method {name: ext.name})
                WITH caller.name AS caller_name,
                     caller.class_name AS caller_class,
                     caller.file_path AS caller_file,
                     ext.name AS method_name,
                     collect({class_name: candidate.class_name,
                              file_path: candidate.file_path}) AS candidates
                WHERE size(candidates) > 1
                RETURN caller_name, caller_class, caller_file, method_name, candidates
                """
            )
            rows = [dict(r) for r in result]

        if not rows:
            return 0

        def path_overlap(path_a: str, path_b: str) -> int:
            parts_a = (path_a or "").replace("\\", "/").split("/")[:-1]
            parts_b = (path_b or "").replace("\\", "/").split("/")[:-1]
            count = 0
            for pa, pb in zip(parts_a, parts_b):
                if pa == pb:
                    count += 1
                else:
                    break
            return count

        resolved_data = []
        for row in rows:
            caller_file = row.get("caller_file") or ""
            candidates = row["candidates"]
            ranked = sorted(
                candidates,
                key=lambda c: path_overlap(caller_file, c.get("file_path") or ""),
                reverse=True,
            )
            best = ranked[0]
            overlap = path_overlap(caller_file, best.get("file_path") or "")
            if overlap >= 1:
                confidence = round(min(1.0, 0.3 + 0.15 * overlap), 2)
                resolved_data.append({
                    "caller_name": row["caller_name"],
                    "caller_class": row["caller_class"],
                    "method_name": row["method_name"],
                    "target_class": best["class_name"],
                    "confidence": confidence,
                    "inferred_reason": f"path_proximity:{overlap}",
                })

        if not resolved_data:
            return 0

        with self.driver.session() as session:
            session.run(
                """
                UNWIND $rows AS row
                MATCH (caller:Method {name: row.caller_name, class_name: row.caller_class})
                MATCH (target:Method {name: row.method_name, class_name: row.target_class})
                MERGE (caller)-[c:CALLS {type: 'external', inferred: true}]->(target)
                SET c.inferred_reason = row.inferred_reason, c.confidence = row.confidence
                """,
                rows=resolved_data,
            )
            session.run(
                """
                UNWIND $rows AS row
                MATCH (caller:Method {name: row.caller_name, class_name: row.caller_class})
                      -[r:CALLS {type: 'external_unknown'}]->(ext:ExternalMethod {name: row.method_name})
                DELETE r
                """,
                rows=resolved_data,
            )

        return len(resolved_data)

    def get_hot_nodes(self, limit=50):
        """获取被调用最多的方法节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Method)<-[r:CALLS]-(caller)
                WITH m, count(r) as degree
                ORDER BY degree DESC
                LIMIT $limit
                RETURN m.name as method_name, m.file_path as file_path, degree
                """,
                limit=limit,
            )
            return [dict(record) for record in result]

    def get_method_count(self):
        """获取总方法数"""
        with self.driver.session() as session:
            result = session.run("MATCH (m:Method) RETURN count(m) as count")
            return result.single()["count"]

    def get_call_count(self):
        """获取总调用关系数"""
        with self.driver.session() as session:
            result = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) as count")
            return result.single()["count"]

    # ==================== Layer 节点管理 ====================

    def add_layer_node(self, layer_name: str, layer_type: str = "base"):
        """创建层级节点（controller/service/facade等）"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (l:Layer {name: $name})
                SET l.layer_type = $layer_type
                """,
                name=layer_name,
                layer_type=layer_type,
            )

    def add_package_node(self, package_name: str, class_count: int = 0, method_count: int = 0):
        """创建包节点"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Package {name: $name})
                SET p.class_count = $class_count, p.method_count = $method_count
                """,
                name=package_name,
                class_count=class_count,
                method_count=method_count,
            )

    def add_contains_relationship(self, layer_name: str, class_name: str):
        """创建层级包含类的关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (l:Layer {name: $layer_name})
                MATCH (c:Class {name: $class_name})
                MERGE (l)-[:CONTAINS]->(c)
                """,
                layer_name=layer_name,
                class_name=class_name,
            )

    def add_package_contains_relationship(self, package_name: str, class_name: str):
        """创建包包含类的关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Package {name: $package_name})
                MATCH (c:Class {name: $class_name})
                MERGE (p)-[:CONTAINS]->(c)
                """,
                package_name=package_name,
                class_name=class_name,
            )

    def add_call_path_relationship(self, start_method: str, end_method: str, depth: int):
        """创建调用路径关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (m1:Method {name: $start_method})
                MATCH (m2:Method {name: $end_method})
                MERGE (m1)-[:CALL_PATH {depth: $depth}]->(m2)
                """,
                start_method=start_method,
                end_method=end_method,
                depth=depth,
            )

    def get_all_layers(self) -> list:
        """获取所有层级节点"""
        with self.driver.session() as session:
            result = session.run("MATCH (l:Layer) RETURN l.name as name, l.layer_type as layer_type")
            return [dict(record) for record in result]

    def get_layer_classes(self, layer_name: str) -> list:
        """获取指定层级下的所有类"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (l:Layer {name: $layer_name})-[:CONTAINS]->(c:Class)
                RETURN c.name as class_name, c.file_path as file_path
                """,
                layer_name=layer_name,
            )
            return [dict(record) for record in result]

    def build_layer_nodes_from_classes(self):
        """从现有类节点构建层级关系"""
        with self.driver.session() as session:
            result = session.run("MATCH (c:Class) RETURN c.name as name, c.file_path as file_path")
            classes = [dict(record) for record in result]

        for cls in classes:
            file_path = cls.get("file_path", "")
            layer_name = self._extract_layer_from_path(file_path)
            if layer_name:
                self.add_layer_node(layer_name)
                self.add_contains_relationship(layer_name, cls["name"])

    def _extract_layer_from_path(self, file_path: str) -> str:
        """从文件路径提取层级"""
        base_layers = {
            "controller", "service", "facade", "biz", "bl",
            "dal", "dao", "model", "entity", "vo", "dto",
            "util", "utils", "helper", "common",
        }
        path_lower = file_path.lower()
        for layer in base_layers:
            if f"/{layer}/" in path_lower or path_lower.endswith(f"/{layer}") or path_lower.endswith(f"/{layer}.java"):
                return layer
        return None

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
