from neo4j import GraphDatabase


class GraphStore:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4j"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            session.run("RETURN 1")

    def add_method_node(self, name, file_path, class_name):
        with self.driver.session() as session:
            session.run(
                "MERGE (m:Method {name: $name, file_path: $file_path, class_name: $class_name})",
                name=name,
                file_path=file_path,
                class_name=class_name
            )

    def add_call_relationship(self, source_method, target_method):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (source:Method {name: $source_method})
                MATCH (target:Method {name: $target_method})
                MERGE (source)-[:CALLS]->(target)
                """,
                source_method=source_method,
                target_method=target_method
            )

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
