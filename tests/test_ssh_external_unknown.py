"""
专项测试：验证 test_java_ssh 在图谱中能稳定产生 external_unknown 调用，
用于暴露老系统动态/反射/运行时绑定盲点。
"""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.config import Config
from src.storage.graph_store import GraphStore
from main import main


def test_external_unknown_for_ssh():
    old_path = Config.PROJECT_PATH
    try:
        Config.PROJECT_PATH = "./fixtures/ssh"
        main(run_neo4j=True, run_vector=False, reset_graph=True)

        with GraphStore() as gs:
            with gs.driver.session() as session:
                row = session.run(
                    """
                    MATCH ()-[r:CALLS]->()
                    WHERE r.type = 'external_unknown'
                    RETURN count(r) AS c
                    """
                ).single()
                unknown_count = row["c"] if row else 0

            print("=" * 60)
            print("test_java_ssh external_unknown 验证")
            print("=" * 60)
            print(f"external_unknown count: {unknown_count}")

            assert unknown_count >= 10, "external_unknown 数量过低，动态盲点不明显"
            print("✅ external_unknown 验证通过")
    finally:
        Config.PROJECT_PATH = old_path


if __name__ == "__main__":
    test_external_unknown_for_ssh()
