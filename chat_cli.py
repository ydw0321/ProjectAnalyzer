"""
GraphRAG CLI 问答入口。

用法:
  python chat_cli.py
"""
from src.logging_utils import setup_logging
from src.llm.graphrag import GraphRAGEngine


HELP_TEXT = """
可用命令:
  /help                         显示帮助
  /exit                         退出
  /trace ClassName.methodName   追踪入口到持久层链路
  /describe layer               总结某层职责（如 controller/service/biz/dal）

普通输入将作为自然语言问题执行 GraphRAG 查询。
"""


def parse_class_method(expr: str):
    if "." not in expr:
        return "", expr
    cls, mtd = expr.split(".", 1)
    return cls.strip(), mtd.strip()


def main():
    setup_logging()
    print("Code-GraphRAG CLI 已启动")
    print(HELP_TEXT)

    with GraphRAGEngine() as engine:
        while True:
            try:
                raw = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出")
                break

            if not raw:
                continue
            if raw in {"/exit", "quit", "exit"}:
                print("退出")
                break
            if raw == "/help":
                print(HELP_TEXT)
                continue

            if raw.startswith("/trace "):
                expr = raw[len("/trace "):].strip()
                cls, mtd = parse_class_method(expr)
                result = engine.trace_entry_to_db(entry_method=mtd, entry_class=cls)
                print("\n[Trace]")
                print(result.get("answer", ""))
                continue

            if raw.startswith("/describe "):
                layer = raw[len("/describe "):].strip().lower()
                result = engine.describe_module(layer)
                print(f"\n[Describe {layer}]")
                print(result.get("answer", ""))
                continue

            result = engine.query(raw)
            print("\n[Answer]")
            print(result.get("answer", ""))
            refs = result.get("refs", [])
            if refs:
                print("\n[Refs]")
                for ref in refs:
                    print(f"- {ref}")


if __name__ == "__main__":
    main()
