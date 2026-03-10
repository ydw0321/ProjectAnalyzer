from src.storage.graph_store import GraphStore
print("Testing GraphStore connection...")
try:
    with GraphStore() as gs:
        print("Connected to Neo4j successfully!")
        print(f"Total methods: {gs.get_method_count()}")
except Exception as e:
    print(f"Failed to connect: {e}")
