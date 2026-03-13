"""
专项测试：对 test_java_ssh 执行图谱与架构树流程（跳过 LLM）。
"""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.config import Config
from main import main


def test_ssh_graph_only():
    old_path = Config.PROJECT_PATH
    try:
        Config.PROJECT_PATH = "./fixtures/ssh"
        print("=" * 60)
        print("test_java_ssh 图谱流程验证")
        print("=" * 60)
        main(enable_llm=False)
        print("✅ graph-only 流程执行完成")
    finally:
        Config.PROJECT_PATH = old_path


if __name__ == "__main__":
    test_ssh_graph_only()
