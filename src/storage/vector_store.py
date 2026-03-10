import chromadb
from src.config import Config


class KnowledgeBase:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="java_code_kb")

    def add_code_chunk(self, chunk_id, summary, code, metadata):
        metadata["raw_code"] = code
        self.collection.add(
            documents=[summary],
            metadatas=[metadata],
            ids=[chunk_id]
        )
