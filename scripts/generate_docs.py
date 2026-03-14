"""
离线文档生成：按层导出 overview，并生成全局 architecture_overview。

默认离线模式：仅从 Neo4j 查询，生成确定性的 Markdown，不调用 LLM。
加 --llm-summary 后才启用 GraphRAG LLM 摘要（需要已嵌入的知识库）。

用法:
  python scripts/generate_docs.py                   # 离线模式
  python scripts/generate_docs.py --llm-summary     # LLM 增强模式
  python scripts/generate_docs.py --layer service   # 仅生成某一层
"""
import argparse
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from collections import defaultdict
from pathlib import Path

from src.logging_utils import setup_logging
from src.tree.config import TreeConfig
from src.tree.query_service import GraphQueryService


# ─── offline helpers ──────────────────────────────────────────────────────────

def _layer_doc_offline(layer: str, query: GraphQueryService) -> str:
    """Generate deterministic Markdown for a single layer from Neo4j data."""
    classes = query.get_class_by_layer(layer)
    class_names = sorted({c.get("class_name", "") for c in classes if c.get("class_name")})

    # Count methods per class for this layer
    all_methods = query.get_all_methods()
    method_by_class: dict[str, list[str]] = defaultdict(list)
    for m in all_methods:
        if m.get("class_name") in set(class_names):
            method_by_class[m["class_name"]].append(m.get("method_name", ""))

    call_stats = query.get_call_statistics()

    lines: list[str] = []
    lines.append(f"# {layer} Layer Overview\n")
    lines.append(f"> Auto-generated (offline). Classes: **{len(class_names)}** | "
                 f"Project total calls: {call_stats.get('total', 'N/A')}\n")

    if not class_names:
        lines.append("_No classes found for this layer in the graph._\n")
        return "\n".join(lines)

    lines.append("## Classes\n")
    for cls in class_names:
        methods = sorted(method_by_class.get(cls, []))
        method_preview = ", ".join(methods[:8])
        if len(methods) > 8:
            method_preview += f" … (+{len(methods) - 8})"
        lines.append(f"- **{cls}** ({len(methods)} methods){': ' + method_preview if method_preview else ''}")

    lines.append("")
    return "\n".join(lines)


def _arch_doc_offline(layer_summaries: list[dict]) -> str:
    """Generate global architecture_overview.md from per-layer data."""
    lines = ["# Architecture Overview\n",
             "> Auto-generated (offline) — run with `--llm-summary` for LLM-enhanced descriptions.\n"]

    for item in layer_summaries:
        layer = item["layer"]
        class_count = item["class_count"]
        lines.append(f"## {layer} 层 ({class_count} classes)\n")
        lines.append(item["body"])
        lines.append("")

    return "\n".join(lines)


# ─── LLM-enhanced helpers ─────────────────────────────────────────────────────

def _layer_doc_llm(layer: str, offline_body: str) -> str:
    """Append LLM summary block to the offline doc."""
    from src.llm.graphrag import GraphRAGEngine
    with GraphRAGEngine() as engine:
        result = engine.describe_module(layer)
    llm_text = result.get("answer", "").strip()
    if not llm_text:
        return offline_body
    return offline_body.rstrip("\n") + "\n\n## LLM Summary\n\n" + llm_text + "\n"


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate layer overview docs from Neo4j graph")
    parser.add_argument("--llm-summary", action="store_true",
                        help="Append LLM-generated summaries (requires embedded knowledge base)")
    parser.add_argument("--layer", metavar="LAYER",
                        help="Generate docs for a specific layer only (e.g. service, dao)")
    args = parser.parse_args()

    setup_logging()
    out_dir = Path("output/docs")
    out_dir.mkdir(parents=True, exist_ok=True)

    target_layers = (
        [args.layer]
        if args.layer
        else sorted(TreeConfig.BASE_LAYERS, key=TreeConfig.get_layer_priority)
    )

    layer_summaries: list[dict] = []

    with GraphQueryService() as query:
        for layer in target_layers:
            body = _layer_doc_offline(layer, query)

            if args.llm_summary:
                try:
                    body = _layer_doc_llm(layer, body)
                except Exception as exc:
                    print(f"[WARN] LLM summary failed for {layer}: {exc}")

            layer_file = out_dir / f"{layer}_overview.md"
            layer_file.write_text(body, encoding="utf-8")
            print(f"[OK] 生成: {layer_file}")

            classes = query.get_class_by_layer(layer)
            layer_summaries.append({
                "layer": layer,
                "class_count": len(classes),
                "body": "\n".join(body.split("\n")[3:]),  # strip header + meta line
            })

    if not args.layer:
        arch_text = _arch_doc_offline(layer_summaries)
        arch_file = out_dir / "architecture_overview.md"
        arch_file.write_text(arch_text, encoding="utf-8")
        print(f"[OK] 生成: {arch_file}")

    mode = "LLM-enhanced" if args.llm_summary else "offline"
    print(f"\n完成 ({mode} 模式) — {len(target_layers)} 层，输出: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
