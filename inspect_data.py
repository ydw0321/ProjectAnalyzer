import chromadb
from src.config import Config

client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
collection = client.get_collection(name="java_code_kb")

print(f"📊 Collection: {collection.name}")
print(f"📈 Total documents: {collection.count()}")
print(f"📋 Metadata keys: {collection.get(limit=1)['metadatas']}")

results = collection.get(limit=5)
print("\n=== Sample Data ===")
for i in range(len(results['ids'])):
    print(f"\n--- Document {i+1} ---")
    print(f"ID: {results['ids'][i]}")
    print(f"Summary: {results['documents'][i][:100]}...")
    print(f"Metadata: {results['metadatas'][i]}")
