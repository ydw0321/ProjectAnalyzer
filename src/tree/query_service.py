"""
图查询服务 - 从 Neo4j 获取图数据用于树生成
"""
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from src.config import Config
from src.tree.config import TreeConfig


class GraphQueryService:
    def __init__(self, uri=None, user=None, password=None):
        uri = uri or Config.NEO4J_URI
        user = user or Config.NEO4J_USER
        password = password or Config.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ==================== 统计查询 ====================
    
    def get_layer_statistics(self) -> List[Dict]:
        """获取各层级统计信息"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Class)
                RETURN c.name as class_name, c.file_path as file_path
            """)
            classes = [dict(record) for record in result]
        
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
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Class)
                RETURN c.name as class_name, c.file_path as file_path
            """)
            classes = [dict(record) for record in result]
        
        return [cls for cls in classes if self._extract_layer(cls['file_path']) == layer]
    
    def get_all_classes(self) -> List[Dict]:
        """获取所有类"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Class)
                RETURN c.name as class_name, c.file_path as file_path
            """)
            return [dict(record) for record in result]
    
    def get_all_methods(self) -> List[Dict]:
        """获取所有方法"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Method)
                RETURN m.name as method_name, m.class_name as class_name, m.file_path as file_path
            """)
            return [dict(record) for record in result]
    
    def get_class_methods(self, class_name: str) -> List[Dict]:
        """获取指定类的所有方法"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Method {class_name: $class_name})
                RETURN m.name as method_name, m.file_path as file_path
            """, class_name=class_name)
            return [dict(record) for record in result]
    
    # ==================== 调用链查询 ====================
    
    def get_entry_methods(self) -> List[Dict]:
        """获取入口方法（Controller/Action层的方法，兼容 Windows 路径）"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Method)-[:BELONGS_TO]->(c:Class)
                OPTIONAL MATCH (m)-[r:CALLS]->()
                WITH m, c, count(r) as out_degree
                RETURN m.name as method_name, m.class_name as class_name, c.file_path as file_path, out_degree
                ORDER BY out_degree DESC, method_name ASC
            """)
            all_methods = [dict(record) for record in result]
        # 用 _extract_layer() 在 Python 侧过滤，避免 Cypher CONTAINS 的路径分隔符问题
        entry_layers = {'controller', 'action'}
        return [m for m in all_methods if self._extract_layer(m['file_path']) in entry_layers]
    
    def get_method_calls(self, method_name: str, class_name: str = None) -> List[Dict]:
        """获取方法调用的其他方法"""
        with self.driver.session() as session:
            if class_name:
                result = session.run("""
                    MATCH (m:Method {name: $method_name, class_name: $class_name})-[r:CALLS]->(callee)
                    RETURN callee.name as callee_name, callee.class_name as callee_class, r.type as call_type
                """, method_name=method_name, class_name=class_name)
            else:
                result = session.run("""
                    MATCH (m:Method {name: $method_name})-[r:CALLS]->(callee)
                    RETURN callee.name as callee_name, callee.class_name as callee_class, r.type as call_type
                """, method_name=method_name)
            return [dict(record) for record in result]
    
    def get_callers_of_method(self, method_name: str, class_name: str = None) -> List[Dict]:
        """获取调用指定方法的方法（上游调用者）"""
        with self.driver.session() as session:
            if class_name:
                result = session.run("""
                    MATCH (caller)-[r:CALLS]->(m:Method {name: $method_name, class_name: $class_name})
                    RETURN caller.name as caller_name, caller.class_name as caller_class, r.type as call_type
                """, method_name=method_name, class_name=class_name)
            else:
                result = session.run("""
                    MATCH (caller)-[r:CALLS]->(m:Method {name: $method_name})
                    RETURN caller.name as caller_name, caller.class_name as caller_class, r.type as call_type
                """, method_name=method_name)
            return [dict(record) for record in result]
    
    def get_downstream_calls(self, method_name: str, class_name: str = None, max_depth: int = None) -> List[Dict]:
        """获取下游调用链（单条 Cypher 变长路径查询，避免 O(n) 轮次数据库访问）"""
        max_depth = max_depth or TreeConfig.MAX_CALL_DEPTH

        params = {'method_name': method_name}
        if class_name:
            params['class_name'] = class_name
            match_clause = "MATCH path = (m:Method {name: $method_name, class_name: $class_name})"
        else:
            match_clause = "MATCH path = (m:Method {name: $method_name})"

        with self.driver.session() as session:
            result = session.run(
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
                """,
                **params
            )
            return [
                {'method': r['callee_name'], 'class': r['callee_class'],
                 'call_type': r['call_type'], 'depth': r['depth'], 'caller': r['caller']}
                for r in result
            ]
    
    def get_upstream_callers(self, method_name: str, class_name: str = None, max_depth: int = None) -> List[Dict]:
        """获取上游调用者链（单条 Cypher 变长路径查询，避免 O(n) 轮次数据库访问）"""
        max_depth = max_depth or TreeConfig.MAX_CALL_DEPTH

        params = {'method_name': method_name}
        node_filter = '{name: $method_name, class_name: $class_name}' if class_name else '{name: $method_name}'
        if class_name:
            params['class_name'] = class_name

        with self.driver.session() as session:
            result = session.run(
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
                """,
                **params
            )
            return [
                {'method': r['caller_name'], 'class': r['caller_class'],
                 'call_type': r['call_type'], 'depth': r['depth'], 'callee': r['callee']}
                for r in result
            ]
    
    def get_data_flow_path(self, start_method: str, start_class: str,
                           end_method: str, end_class: str = None) -> List[List[str]]:
        """获取两点之间的数据流路径（BFS搜索，修复 end_class 默认值和匹配逻辑）"""
        visited = set()
        queue = [([f"{start_class}.{start_method}"], start_method, start_class)]

        while queue:
            path, curr_method, curr_class = queue.pop(0)

            # 修复：end_class 为 None 时只比较方法名；否则同时比较类名和方法名
            method_match = curr_method == end_method
            class_match = (end_class is None) or (curr_class == end_class)
            if method_match and class_match:
                return [path]

            key = (curr_method, curr_class)
            if key in visited:
                continue
            visited.add(key)

            calls = self.get_method_calls(curr_method, curr_class)
            for call in calls:
                new_path = path + [f"{call['callee_class']}.{call['callee_name']}"]
                queue.append((new_path, call['callee_name'], call['callee_class']))

        return []
    
    # ==================== 调用关系统计 ====================
    
    def get_call_statistics(self) -> Dict:
        """获取调用关系统计（单次查询，修复 .peek() 兼容性问题）"""
        with self.driver.session() as session:
            result = session.run("""
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
