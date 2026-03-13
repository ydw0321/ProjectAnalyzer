"""
批量 LLM 摘要索引器 - 为所有方法生成摘要并存入 ChromaDB，支持增量更新。
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from tqdm import tqdm

from src.storage.vector_store import KnowledgeBase
from src.llm.processor import LLMProcessor
from src.tree.config import extract_layer


class BatchIndexer:
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        self.kb = knowledge_base or KnowledgeBase()

    def _make_chunk_id(self, method: dict) -> str:
        """生成唯一的 chunk_id（文件路径+类名+方法名）"""
        return (
            f"{method['file_path']}::{method.get('class_name', '')}::{method['name']}"
            .replace(os.sep, "/")
        )

    def _method_key(self, method: dict) -> str:
        class_name = method.get("class_name", "")
        method_name = method.get("name", "")
        return f"{class_name}.{method_name}".strip(".")

    def _index_one(
        self,
        method: dict,
        call_count: int = 0,
        callers_count: int = 0,
        skip_existing: bool = True,
    ) -> str:
        """
        索引单个方法。
        Returns:
            'skipped' 如果已存在且 skip_existing=True
            chunk_id   如果成功写入
        Raises:
            Exception  如果 LLM 调用或写库失败
        """
        chunk_id = self._make_chunk_id(method)
        # 批量模式下由 index_all 统一预过滤，避免每条都访问一次 Chroma。
        if skip_existing and self.kb.exists(chunk_id):
            return "skipped"

        file_path = method.get("file_path", "")
        class_name = method.get("class_name", "")
        layer = extract_layer(file_path)

        # 从 fields 提取字段依赖名称
        field_deps = [
            f.get("name", "") for f in method.get("fields", []) if f.get("name")
        ] or None

        git_info = method.get("git_info", {"author": "Unknown", "message": "批量索引"})

        summary = LLMProcessor.generate_summary(
            method_name=method["name"],
            code=method.get("code", ""),
            git_info=git_info,
            class_name=class_name,
            layer=layer,
            field_deps=field_deps,
        )

        metadata = {
            "file_path": file_path,
            "method_name": method["name"],
            "class_name": class_name,
            "layer": layer,
            "call_count": call_count,
            "callers_count": callers_count,
        }
        self.kb.add_code_chunk(chunk_id, summary, method.get("code", ""), metadata)
        return chunk_id

    def index_all(
        self,
        method_index: List[dict],
        call_counts: Optional[Dict[str, int]] = None,
        caller_counts: Optional[Dict[str, int]] = None,
        top_n: Optional[int] = None,
        max_workers: int = 4,
        skip_existing: bool = True,
    ) -> dict:
        """
        全量索引所有方法。

        Args:
            method_index:   方法列表，每项含 name/class_name/file_path/code
            call_counts:    {方法名: 下游调用数}（用于热度排序）
            caller_counts:  {方法名: 上游调用数}
            top_n:          仅索引前 N 个方法（按调用热度降序）
            max_workers:    并发线程数（受 LLM QPS 限制，建议 2-8）
            skip_existing:  True 则跳过已索引方法（增量更新）

        Returns:
            {'total': int, 'indexed': int, 'skipped': int, 'failed': int}
        """
        call_counts = call_counts or {}
        caller_counts = caller_counts or {}

        prioritized_methods = method_index
        if top_n is not None and top_n > 0:
            prioritized_methods = sorted(
                method_index,
                key=lambda m: call_counts.get(self._method_key(m), call_counts.get(m.get("name", ""), 0)),
                reverse=True,
            )[:top_n]

        stats = {
            "total": len(prioritized_methods),
            "indexed": 0,
            "skipped": 0,
            "failed": 0,
        }

        pending_methods = prioritized_methods
        if skip_existing and prioritized_methods:
            existing_ids = self.kb.get_all_ids()
            pending_methods = [
                method for method in prioritized_methods
                if self._make_chunk_id(method) not in existing_ids
            ]
            stats["skipped"] = len(prioritized_methods) - len(pending_methods)

        if not pending_methods:
            return stats

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._index_one,
                    method,
                    call_counts.get(self._method_key(method), call_counts.get(method["name"], 0)),
                    caller_counts.get(self._method_key(method), caller_counts.get(method["name"], 0)),
                    False,
                ): method
                for method in pending_methods
            }

            with tqdm(total=len(futures), desc="📚 全量索引方法摘要") as pbar:
                for future in as_completed(futures):
                    method = futures[future]
                    try:
                        result = future.result()
                        if result == "skipped":
                            stats["skipped"] += 1
                        else:
                            stats["indexed"] += 1
                    except Exception as e:
                        stats["failed"] += 1
                        print(
                            f"\n⚠️ 索引失败 [{method.get('class_name')}.{method.get('name')}]: {e}"
                        )
                    pbar.update(1)

        return stats
