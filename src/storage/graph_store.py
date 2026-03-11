from neo4j import GraphDatabase
from src.config import Config


class GraphStore:
    def __init__(self, uri=None, user=None, password=None):
        uri = uri or Config.NEO4J_URI
        user = user or Config.NEO4J_USER
        password = password or Config.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            session.run("RETURN 1")

    def add_class_node(self, class_name, file_path):
        """创建类节点"""
        with self.driver.session() as session:
            session.run(
                "MERGE (c:Class {name: $name, file_path: $file_path})",
                name=class_name,
                file_path=file_path
            )

    def add_method_node(self, name, class_name, file_path):
        """创建方法节点"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (m:Method {name: $name})
                SET m.class_name = $class_name, m.file_path = $file_path
                """,
                name=name,
                class_name=class_name,
                file_path=file_path
            )

    def add_call_relationship(self, caller, callee, caller_class=None, callee_class=None, call_type='internal'):
        """创建方法调用关系（支持跨类调用）"""
        with self.driver.session() as session:
            # 动态构建查询
            if call_type == 'external':
                # 跨类调用 - 通过类名匹配
                if caller_class and callee_class and callee_class != 'Unknown':
                    session.run(
                        """
                        MATCH (caller:Method {name: $caller})
                        MATCH (callee:Method {name: $callee, class_name: $callee_class})
                        MERGE (caller)-[:CALLS {via_field: $via_field, type: 'external'}]->(callee)
                        """,
                        caller=caller,
                        callee=callee,
                        callee_class=callee_class,
                        via_field=caller + '_to_' + callee
                    )
                else:
                    # 目标类未知，仅记录调用关系
                    session.run(
                        """
                        MATCH (caller:Method {name: $caller})
                        MERGE (caller)-[:CALLS {type: 'external_unknown'}]->(callee:ExternalMethod {name: $callee})
                        """,
                        caller=caller,
                        callee=callee
                    )
            else:
                # 内部调用
                session.run(
                    """
                    MATCH (caller:Method {name: $caller})
                    MATCH (callee:Method {name: $callee})
                    MERGE (caller)-[:CALLS {type: 'internal'}]->(callee)
                    """,
                    caller=caller,
                    callee=callee
                )

    def add_belongs_to_relationship(self, method_name, class_name):
        """创建方法属于类的关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (m:Method {name: $method_name})
                MATCH (c:Class {name: $class_name})
                MERGE (m)-[:BELONGS_TO]->(c)
                """,
                method_name=method_name,
                class_name=class_name
            )

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
                limit=limit
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

    def add_layer_node(self, layer_name: str, layer_type: str = 'base'):
        """创建层级节点（controller/service/facade等）"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (l:Layer {name: $name})
                SET l.layer_type = $layer_type
                """,
                name=layer_name,
                layer_type=layer_type
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
                method_count=method_count
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
                class_name=class_name
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
                class_name=class_name
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
                depth=depth
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
                layer_name=layer_name
            )
            return [dict(record) for record in result]

    def build_layer_nodes_from_classes(self):
        """从现有类节点构建层级关系"""
        # 获取所有类并分析其层级
        with self.driver.session() as session:
            result = session.run("MATCH (c:Class) RETURN c.name as name, c.file_path as file_path")
            classes = [dict(record) for record in result]

        # 提取层级并创建节点
        for cls in classes:
            file_path = cls.get('file_path', '')
            layer_name = self._extract_layer_from_path(file_path)
            if layer_name:
                self.add_layer_node(layer_name)
                self.add_contains_relationship(layer_name, cls['name'])

    def _extract_layer_from_path(self, file_path: str) -> str:
        """从文件路径提取层级"""
        base_layers = {'controller', 'service', 'facade', 'biz', 'bl', 'dal', 'dao', 'model', 'entity', 'vo', 'dto'}
        path_lower = file_path.lower()
        for layer in base_layers:
            if f'/{layer}/' in path_lower or path_lower.endswith(f'/{layer}') or path_lower.endswith(f'/{layer}.java'):
                return layer
        return None

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
