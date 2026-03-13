"""
GraphRAG 引擎：向量召回 + 图扩展 + LLM 生成回答。
"""
from typing import List, Dict, Optional, Tuple

from src.llm.processor import LLMProcessor
from src.storage.vector_store import KnowledgeBase
from src.tree.query_service import GraphQueryService


class GraphRAGEngine:
    def __init__(
        self,
        kb: Optional[KnowledgeBase] = None,
        query_service: Optional[GraphQueryService] = None,
    ):
        self.kb = kb or KnowledgeBase()
        self.query_service = query_service or GraphQueryService()

    def close(self):
        if self.query_service:
            self.query_service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _format_path_lines(self, method_name: str, class_name: str = "", depth: int = 2) -> List[str]:
        lines: List[str] = []
        downstream = self.query_service.get_downstream_calls(method_name, class_name or None, max_depth=depth)
        upstream = self.query_service.get_upstream_callers(method_name, class_name or None, max_depth=depth)

        for item in upstream:
            caller = f"{item.get('class')}.{item.get('method')}"
            callee = f"{class_name}.{method_name}" if class_name else method_name
            lines.append(
                f"上游[{item.get('depth')}]: {caller} -> {callee} (type={item.get('call_type')})"
            )

        for item in downstream:
            caller = item.get('caller', method_name)
            callee = f"{item.get('class')}.{item.get('method')}"
            lines.append(
                f"下游[{item.get('depth')}]: {caller} -> {callee} (type={item.get('call_type')})"
            )
        return lines

    def _build_context(
        self,
        question: str,
        recalled: List[Dict],
        selected_class: Optional[str] = None,
        selected_method: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        refs: List[str] = []
        context_blocks: List[str] = []

        if selected_method:
            anchor = f"{selected_class}.{selected_method}" if selected_class else selected_method
            refs.append(anchor)
            graph_lines = self._format_path_lines(selected_method, selected_class or "", depth=2)
            context_blocks.append("## 当前焦点节点调用链\n" + "\n".join(graph_lines[:30]))

        for item in recalled:
            meta = item.get("metadata", {}) or {}
            class_name = meta.get("class_name", "")
            method_name = meta.get("method_name", "")
            if not method_name:
                continue
            ref_name = f"{class_name}.{method_name}" if class_name else method_name
            refs.append(ref_name)
            summary = item.get("summary", "")
            graph_lines = self._format_path_lines(method_name, class_name, depth=2)
            block = (
                f"### 相关方法: {ref_name}\n"
                f"- 层级: {meta.get('layer', 'unknown')}\n"
                f"- 摘要: {summary}\n"
                f"- 调用链:\n"
                + "\n".join([f"  - {line}" for line in graph_lines[:20]])
            )
            context_blocks.append(block)

        prompt = (
            "你正在帮助用户快速理解一个历史老项目。"
            "请优先基于给定上下文回答，避免无依据推断。\n\n"
            f"## 用户问题\n{question}\n\n"
            "## 图与语义上下文\n"
            + "\n\n".join(context_blocks[:8])
            + "\n\n## 输出要求\n"
              "1) 先给结论\n"
              "2) 列出关键调用链\n"
              "3) 给出涉及的核心类/方法\n"
              "4) 如上下文不足，明确说明缺失信息"
        )
        return prompt, sorted(set(refs))

    def _run_llm(self, prompt: str, question: str = "请根据上下文回答用户问题") -> str:
        # 使用问答专用提示词，避免被“方法摘要模板”误导
        return LLMProcessor.generate_qa_answer(
            question=question,
            context=prompt,
        )

    def query(
        self,
        question: str,
        selected_class: Optional[str] = None,
        selected_method: Optional[str] = None,
        n_results: int = 10,
        filter_layer: Optional[str] = None,
    ) -> Dict:
        recalled = self.kb.search(question, n_results=n_results, filter_layer=filter_layer)
        prompt, refs = self._build_context(
            question=question,
            recalled=recalled,
            selected_class=selected_class,
            selected_method=selected_method,
        )
        answer = LLMProcessor.generate_qa_answer(question=question, context=prompt)
        return {
            "answer": answer,
            "refs": refs,
            "recalled": recalled,
        }

    def trace_entry_to_db(self, entry_method: str, entry_class: str = "") -> Dict:
        lines = self._format_path_lines(entry_method, entry_class, depth=6)
        prompt = (
            "请把下面的调用链整理成从入口到持久层（DAL/DAO/Repository）的中文说明。\n"
            "输出应包含：主链路、关键分支、潜在断链风险。\n\n"
            + "\n".join(lines)
        )
        answer = self._run_llm(prompt, question="请将入口到持久层的调用链整理为中文说明")
        return {
            "entry": f"{entry_class}.{entry_method}" if entry_class else entry_method,
            "answer": answer,
            "trace_lines": lines,
        }

    def describe_module(self, layer_name: str) -> Dict:
        docs = self.kb.search(
            query=f"{layer_name} 层 核心职责",
            n_results=30,
            filter_layer=layer_name,
        )
        method_lines = []
        for item in docs:
            meta = item.get("metadata", {})
            method_lines.append(
                f"- {meta.get('class_name', '')}.{meta.get('method_name', '')}: {item.get('summary', '')}"
            )
        prompt = (
            f"请总结 {layer_name} 层在该老项目中的职责边界、核心对象、典型调用模式。\n"
            "要求: 先总体后细节，列出3个风险点。\n\n"
            "### 方法摘要样本\n"
            + "\n".join(method_lines[:50])
        )
        answer = self._run_llm(prompt, question=f"请总结 {layer_name} 层职责边界、核心对象和风险")
        return {
            "layer": layer_name,
            "answer": answer,
            "samples": method_lines[:50],
        }
