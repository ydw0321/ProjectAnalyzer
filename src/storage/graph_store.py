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

    def add_call_relationship(self, caller, callee):
        """创建方法调用关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (caller:Method {name: $caller})
                MATCH (callee:Method {name: $callee})
                MERGE (caller)-[:CALLS]->(callee)
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

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
