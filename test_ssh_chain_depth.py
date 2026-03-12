"""
专项测试：验证 test_java_ssh 的深链路阈值与超大类规模。
"""
from main import main
from src.config import Config
from src.parser.java_parser import JavaParser
from src.tree import GraphQueryService


def test_chain_depth_threshold():
    old_path = Config.PROJECT_PATH
    try:
        Config.PROJECT_PATH = "./test_java_ssh"
        main(enable_llm=False)

        with GraphQueryService() as query:
            downstream = query.get_downstream_calls("start", "DeepChainCoordinator", max_depth=20)
            max_depth = max((d.get("depth", 0) for d in downstream), default=0)

        parser = JavaParser()
        result = parser.extract_with_calls("./test_java_ssh/service/impl/order/LegacyTicketMonsterService.java")
        monster_methods = len(result.get("methods", []))

        print("=" * 60)
        print("test_java_ssh 深度阈值验证")
        print("=" * 60)
        print(f"DeepChainCoordinator 下游最大深度: {max_depth}")
        print(f"LegacyTicketMonsterService 方法数量: {monster_methods}")

        assert max_depth >= 11, "调用链深度不足，未达到 10+ 深链压测目标"
        assert monster_methods >= 25, "超大类方法数不足，未达到 monster 规模目标"
        print("✅ 深链阈值与超大类规模验证通过")
    finally:
        Config.PROJECT_PATH = old_path


if __name__ == "__main__":
    test_chain_depth_threshold()