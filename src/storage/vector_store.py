import chromadb
from src.config import Config
from typing import List, Optional, Dict


class KnowledgeBase:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="java_code_kb")

    def add_code_chunk(self, chunk_id: str, summary: str, code: str, metadata: dict):
        """写入（upsert）一个代码块，支持重复写入覆盖"""
        metadata = dict(metadata)
        metadata["raw_code"] = code
        self.collection.upsert(
            documents=[summary],
            metadatas=[metadata],
            ids=[chunk_id]
        )

    def exists(self, chunk_id: str) -> bool:
        """检查 chunk_id 是否已经索引"""
        result = self.collection.get(ids=[chunk_id], include=[])
        return len(result["ids"]) > 0

    def get_all_ids(self, page_size: int = 5000) -> set[str]:
        """分页读取所有已索引 ID，便于增量任务做批量跳过。"""
        all_ids: set[str] = set()
        offset = 0
        while True:
            result = self.collection.get(limit=page_size, offset=offset, include=[])
            ids = result.get("ids", [])
            if not ids:
                break
            all_ids.update(ids)
            if len(ids) < page_size:
                break
            offset += page_size
        return all_ids

    def count(self) -> int:
        """返回当前索引的文档总数"""
        return self.collection.count()

    def search(
        self,
        query: str,
        n_results: int = 10,
        filter_layer: Optional[str] = None,
    ) -> List[Dict]:
        """语义搜索，可选按 layer 过滤。返回列表，每项包含 id/summary/metadata/distance"""
        total = self.collection.count()
        if total == 0:
            return []
        n = min(n_results, total)
        kwargs: dict = {
            "query_texts": [query],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_layer:
            kwargs["where"] = {"layer": filter_layer}
        result = self.collection.query(**kwargs)
        items = []
        for i, doc_id in enumerate(result["ids"][0]):
            items.append({
                "id": doc_id,
                "summary": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            })
        return items
