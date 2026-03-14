"""
图查询服务 - 从 Neo4j 获取图数据用于树生成
"""
import logging
from typing import List, Dict, Optional
from neo4j import GraphDatabase, Query
from src.config import Config
from src.tree.config import TreeConfig


logger = logging.getLogger(__name__)


class GraphQueryService:
    def __init__(self, uri=None, user=None, password=None):
        uri = uri or Config.NEO4J_URI
        user = user or Config.NEO4J_USER
        password = password or Config.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def _normalize_depth(self, max_depth: Optional[int]) -> int:
        depth = max_depth if max_depth is not None else TreeConfig.MAX_CALL_DEPTH
        return max(1, min(depth, TreeConfig.HARD_MAX_CALL_DEPTH))

    def _normalize_limit(self, limit: Optional[int] = None) -> int:
        limit = limit if limit is not None else TreeConfig.MAX_QUERY_RESULTS
        return max(1, min(limit, TreeConfig.MAX_QUERY_RESULTS))

    def _run_query(self, query_text: str, params: Optional[Dict] = None) -> List[Dict]:
        params = params or {}
        query = Query(query_text, timeout=TreeConfig.QUERY_TIMEOUT)
        with self.driver.session() as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]
    
    def close(self):
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ==================== 统计查询 ====================
    
    def get_layer_statistics(self) -> List[Dict]:
        """获取各层级统计信息"""
        classes = self._run_query("""
            MATCH (c:Class)
            RETURN c.name as class_name, c.file_path as file_path
        """)
        
        # 按文件路径分析层级
        layer_stats = {}
        for cls in classes:
            file_path = cls.get('file_path', '')
            layer = self._extract_layer(file_path)
            if layer not in layer_stats:
                layer_stats[layer] = {'layer': layer, 'class_count': 0, 'classes': []}
            layer_stats[layer]['class_count'] += 1
            layer_stats[layer]['classes'].append(cls['class_name'])
        
        return list(layer_stats.values())
    
    def _extract_layer(self, file_path: str) -> str:
        """从文件路径提取层级（兼容 Windows 反斜杠和 Unix 正斜杠）"""
        path_lower = file_path.lower().replace('\\', '/')
        for base_layer in TreeConfig.BASE_LAYERS:
            if f'/{base_layer}/' in path_lower or path_lower.endswith(f'/{base_layer}') or path_lower.endswith(f'/{base_layer}.java'):
                return base_layer
        return 'other'
    
    def get_class_by_layer(self, layer: str) -> List[Dict]:
        """获取指定层级的所有类"""
        classes = self._run_query("""
            MATCH (c:Class)
            RETURN c.name as class_name, c.file_path as file_path
        """)
        
        return [cls for cls in classes if self._extract_layer(cls['file_path']) == layer]
    
    def get_all_classes(self) -> List[Dict]:
        """获取所有类"""
        result = self._run_query("""
            MATCH (c:Class)
            RETURN c.name as class_name, c.file_path as file_path
        """)
        return result
    
    def get_all_methods(self) -> List[Dict]:
        """获取所有方法"""
        result = self._run_query("""
            MATCH (m:Method)
            RETURN m.name as method_name, m.class_name as class_name, m.file_path as file_path
        """)
        return result
    
    def get_class_methods(self, class_name: str) -> List[Dict]:
        """获取指定类的所有方法"""
        result = self._run_query("""
            MATCH (m:Method {class_name: $class_name})
            RETURN m.name as method_name, m.file_path as file_path
        """, {'class_name': class_name})
        return result

    def _entry_score(self, method: Dict) -> int:
        """Heuristic score for entry method candidates.

        Higher score means more likely to be an externally-invoked entrypoint.
        """
        method_name = (method.get('method_name') or '').lower()
        class_name = (method.get('class_name') or '').lower()
        file_path = (method.get('file_path') or '').lower().replace('\\', '/')
        out_degree = int(method.get('out_degree') or 0)
        layer = self._extract_layer(file_path)

        score = 0

        # Layer/path signal
        if layer in {'controller', 'action'}:
            score += 8
        if any(token in file_path for token in ('/interf/', '/interface/', '/api/', '/web/', '/struts/')):
            score += 4

        # Class naming signal
        if class_name.endswith('action') or class_name.endswith('controller'):
            score += 8
        if class_name.endswith('interf') or class_name.endswith('api'):
            score += 4

        # Method naming signal
        if method_name in {'execute', 'invoke', 'process', 'dispatch'}:
            score += 7
        if method_name.startswith(('do', 'handle', 'submit', 'query', 'list', 'get', 'find', 'send')):
            score += 2

        # Entrypoints usually have fanout
        if out_degree >= 3:
            score += 2
        if out_degree >= 10:
            score += 2

        # Filter obvious non-entry helpers
        if method_name.startswith(('set', 'get', 'is')) and out_degree == 0:
            score -= 5

        return score
    
    # ==================== 调用链查询 ====================
    
    def get_entry_methods(self) -> List[Dict]:
        """获取入口方法（多信号启发式，兼容传统 Action/Interf 风格项目）。"""
        all_methods = self._run_query("""
            MATCH (m:Method)-[:BELONGS_TO]->(c:Class)
            OPTIONAL MATCH (m)-[r:CALLS]->()
            WITH m, c, count(r) as out_degree
            RETURN m.name as method_name, m.class_name as class_name, c.file_path as file_path, out_degree
            ORDER BY out_degree DESC, method_name ASC
            LIMIT $limit
        """, {'limit': self._normalize_limit(1000)})

        scored = []
        for method in all_methods:
            score = self._entry_score(method)
            if score >= 8:
                item = dict(method)
                item['entry_score'] = score
                scored.append(item)

        scored.sort(key=lambda x: (x.get('entry_score', 0), x.get('out_degree', 0)), reverse=True)
        return scored[:200]
    
    def get_method_calls(self, method_name: str, class_name: str = None, limit: int = None) -> List[Dict]:
        """获取方法调用的其他方法"""
        limit = self._normalize_limit(limit or TreeConfig.MAX_METHOD_FANOUT)
        if class_name:
            result = self._run_query("""
                MATCH (m:Method {name: $method_name, class_name: $class_name})-[r:CALLS]->(callee)
                RETURN callee.name as callee_name, callee.class_name as callee_class, r.type as call_type
                LIMIT $limit
            """, {'method_name': method_name, 'class_name': class_name, 'limit': limit})
        else:
            result = self._run_query("""
                MATCH (m:Method {name: $method_name})-[r:CALLS]->(callee)
                RETURN callee.name as callee_name, callee.class_name as callee_class, r.type as call_type
                LIMIT $limit
            """, {'method_name': method_name, 'limit': limit})
        return result
    
    def get_callers_of_method(self, method_name: str, class_name: str = None, limit: int = None) -> List[Dict]:
        """获取调用指定方法的方法（上游调用者）"""
        limit = self._normalize_limit(limit or TreeConfig.MAX_METHOD_FANOUT)
        if class_name:
            result = self._run_query("""
                MATCH (caller)-[r:CALLS]->(m:Method {name: $method_name, class_name: $class_name})
                RETURN caller.name as caller_name, caller.class_name as caller_class, r.type as call_type
                LIMIT $limit
            """, {'method_name': method_name, 'class_name': class_name, 'limit': limit})
        else:
            result = self._run_query("""
                MATCH (caller)-[r:CALLS]->(m:Method {name: $method_name})
                RETURN caller.name as caller_name, caller.class_name as caller_class, r.type as call_type
                LIMIT $limit
            """, {'method_name': method_name, 'limit': limit})
        return result
    
    def get_downstream_calls(self, method_name: str, class_name: str = None, max_depth: int = None, limit: int = None) -> List[Dict]:
        """获取下游调用链（单条 Cypher 变长路径查询，避免 O(n) 轮次数据库访问）"""
        max_depth = self._normalize_depth(max_depth)
        limit = self._normalize_limit(limit)

        params = {'method_name': method_name}
        if class_name:
            params['class_name'] = class_name
            match_clause = "MATCH path = (m:Method {name: $method_name, class_name: $class_name})"
        else:
            match_clause = "MATCH path = (m:Method {name: $method_name})"

        params['limit'] = limit
        result = self._run_query(
            f"""
            {match_clause}-[:CALLS*1..{max_depth}]->(callee)
            WITH callee, length(path) AS depth,
                 last([r IN relationships(path) | r.type]) AS call_type,
                 [n IN nodes(path) | n.name][-2] AS caller_name
            ORDER BY depth ASC
            WITH callee, head(collect({{depth: depth, call_type: call_type, caller: caller_name}})) AS shortest
            RETURN callee.name AS callee_name, callee.class_name AS callee_class,
                   shortest.depth AS depth, shortest.call_type AS call_type,
                   shortest.caller AS caller
            LIMIT $limit
            """,
            params,
        )
        return [
            {'method': r['callee_name'], 'class': r['callee_class'],
             'call_type': r['call_type'], 'depth': r['depth'], 'caller': r['caller']}
            for r in result
        ]
    
    def get_upstream_callers(self, method_name: str, class_name: str = None, max_depth: int = None, limit: int = None) -> List[Dict]:
        """获取上游调用者链（单条 Cypher 变长路径查询，避免 O(n) 轮次数据库访问）"""
        max_depth = self._normalize_depth(max_depth)
        limit = self._normalize_limit(limit)

        params = {'method_name': method_name}
        node_filter = '{name: $method_name, class_name: $class_name}' if class_name else '{name: $method_name}'
        if class_name:
            params['class_name'] = class_name

        params['limit'] = limit
        result = self._run_query(
            f"""
            MATCH path = (caller)-[:CALLS*1..{max_depth}]->(m:Method {node_filter})
            WITH caller, length(path) AS depth,
                 head([r IN relationships(path) | r.type]) AS call_type,
                 [n IN nodes(path) | n.name][1] AS callee_name
            ORDER BY depth ASC
            WITH caller, head(collect({{depth: depth, call_type: call_type, callee: callee_name}})) AS shortest
            RETURN caller.name AS caller_name, caller.class_name AS caller_class,
                   shortest.depth AS depth, shortest.call_type AS call_type,
                   shortest.callee AS callee
            LIMIT $limit
            """,
            params,
        )
        return [
            {'method': r['caller_name'], 'class': r['caller_class'],
             'call_type': r['call_type'], 'depth': r['depth'], 'callee': r['callee']}
            for r in result
        ]
    
    def get_data_flow_path(self, start_method: str, start_class: str,
                           end_method: str, end_class: str = None) -> List[List[str]]:
        """获取两点之间的数据流路径（BFS搜索，修复 end_class 默认值和匹配逻辑）"""
        max_depth = self._normalize_depth(TreeConfig.MAX_CALL_DEPTH)
        visited = set()
        queue = [([f"{start_class}.{start_method}"], start_method, start_class)]

        while queue:
            path, curr_method, curr_class = queue.pop(0)
            if len(path) > max_depth + 1 or len(visited) >= TreeConfig.MAX_NODE_COUNT:
                logger.warning("数据流路径搜索提前截断: visited=%s, path_len=%s", len(visited), len(path))
                break

            # 修复：end_class 为 None 时只比较方法名；否则同时比较类名和方法名
            method_match = curr_method == end_method
            class_match = (end_class is None) or (curr_class == end_class)
            if method_match and class_match:
                return [path]

            key = (curr_method, curr_class)
            if key in visited:
                continue
            visited.add(key)

            calls = self.get_method_calls(curr_method, curr_class, limit=TreeConfig.MAX_METHOD_FANOUT)
            for call in calls:
                new_path = path + [f"{call['callee_class']}.{call['callee_name']}"]
                queue.append((new_path, call['callee_name'], call['callee_class']))

        return []
    
    # ==================== 调用关系统计 ====================
    
    def get_call_statistics(self) -> Dict:
        """获取调用关系统计（单次查询，修复 .peek() 兼容性问题）"""
        result = self._run_query("""
            MATCH ()-[r:CALLS]->()
            RETURN r.type AS call_type, count(r) AS count
        """)
        stats = {'internal': 0, 'external': 0, 'external_unknown': 0}
        for record in result:
            call_type = record['call_type']
            if call_type in stats:
                stats[call_type] = record['count']
        stats['total'] = stats['internal'] + stats['external'] + stats['external_unknown']
        return stats
