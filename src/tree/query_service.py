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
        """从文件路径提取层级"""
        path_lower = file_path.lower()
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
        """获取入口方法（Controller层的方法）"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Method)-[:BELONGS_TO]->(c:Class)
                WHERE c.file_path CONTAINS '/controller/' OR c.file_path CONTAINS '/action/'
                OPTIONAL MATCH (m)-[r:CALLS]->()
                WITH m, c, count(r) as out_degree
                RETURN m.name as method_name, m.class_name as class_name, c.file_path as file_path, out_degree
                ORDER BY out_degree DESC, method_name ASC
            """)
            return [dict(record) for record in result]
    
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
        """获取下游调用链"""
        max_depth = max_depth or TreeConfig.MAX_CALL_DEPTH
        
        downstream = []
        visited = set()
        queue = [(method_name, class_name, 0)]
        
        while queue:
            curr_method, curr_class, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            key = (curr_method, curr_class)
            if key in visited:
                continue
            visited.add(key)
            
            calls = self.get_method_calls(curr_method, curr_class)
            for call in calls:
                downstream.append({
                    'method': call['callee_name'],
                    'class': call['callee_class'],
                    'call_type': call['call_type'],
                    'depth': depth + 1,
                    'caller': curr_method
                })
                queue.append((call['callee_name'], call['callee_class'], depth + 1))
        
        return downstream
    
    def get_upstream_callers(self, method_name: str, class_name: str = None, max_depth: int = None) -> List[Dict]:
        """获取上游调用者链"""
        max_depth = max_depth or TreeConfig.MAX_CALL_DEPTH
        
        upstream = []
        visited = set()
        queue = [(method_name, class_name, 0)]
        
        while queue:
            curr_method, curr_class, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            key = (curr_method, curr_class)
            if key in visited:
                continue
            visited.add(key)
            
            callers = self.get_callers_of_method(curr_method, curr_class)
            for caller in callers:
                upstream.append({
                    'method': caller['caller_name'],
                    'class': caller['caller_class'],
                    'call_type': caller['call_type'],
                    'depth': depth + 1,
                    'callee': curr_method
                })
                queue.append((caller['caller_name'], caller['caller_class'], depth + 1))
        
        return upstream
    
    def get_data_flow_path(self, start_method: str, start_class: str, 
                           end_method: str, end_class: str = None) -> List[List[str]]:
        """获取两点之间的数据流路径（BFS搜索）"""
        if not end_class:
            end_class = end_method
        
        visited = set()
        queue = [([f"{start_class}.{start_method}"], start_method, start_class)]
        
        while queue:
            path, curr_method, curr_class = queue.pop(0)
            
            if curr_method == end_method:
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
        """获取调用关系统计"""
        with self.driver.session() as session:
            # 内部调用统计
            internal_result = session.run("""
                MATCH ()-[r:CALLS {type: 'internal'}]->()
                RETURN count(r) as count
            """)
            internal_count = internal_result.single()["count"] if internal_result.peek() else 0
            
            # 外部调用统计
            external_result = session.run("""
                MATCH ()-[r:CALLS {type: 'external'}]->()
                RETURN count(r) as count
            """)
            external_count = external_result.single()["count"] if external_result.peek() else 0
            
            # 未知调用统计
            unknown_result = session.run("""
                MATCH ()-[r:CALLS {type: 'external_unknown'}]->()
                RETURN count(r) as count
            """)
            unknown_count = unknown_result.single()["count"] if unknown_result.peek() else 0
            
            return {
                'internal': internal_count,
                'external': external_count,
                'external_unknown': unknown_count,
                'total': internal_count + external_count + unknown_count
            }
