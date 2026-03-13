"""
离线文档生成：按层导出 overview，并生成全局 architecture_overview。
"""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from pathlib import Path

from src.logging_utils import setup_logging
from src.llm.graphrag import GraphRAGEngine
from src.tree.config import TreeConfig


def main():
    setup_logging()
    out_dir = Path("output/docs")
    out_dir.mkdir(parents=True, exist_ok=True)

    with GraphRAGEngine() as engine:
        overview_blocks = ["# Architecture Overview\n"]

        for layer in sorted(TreeConfig.BASE_LAYERS, key=TreeConfig.get_layer_priority):
            result = engine.describe_module(layer)
            text = result.get("answer", "")
            layer_file = out_dir / f"{layer}_overview.md"
            layer_file.write_text(f"# {layer} Layer Overview\n\n{text}\n", encoding="utf-8")
            print(f"✅ 生成: {layer_file}")

            overview_blocks.append(f"## {layer} 层")
            overview_blocks.append(text)
            overview_blocks.append("")

        arch_file = Path("output/docs/architecture_overview.md")
        arch_file.write_text("\n".join(overview_blocks), encoding="utf-8")
        print(f"✅ 生成: {arch_file}")


if __name__ == "__main__":
    main()
