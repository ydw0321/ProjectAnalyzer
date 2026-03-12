"""
专项测试：验证第二批深链路与同名方法污染是否进入解析结果。
"""
from src.scanner.scanner import scan_java_files
from src.parser.java_parser import JavaParser


def test_deep_chain_parser_coverage():
    parser = JavaParser()
    files = scan_java_files("./test_java_ssh")

    target = None
    for path in files:
        if path.endswith("LegacyMegaWorkflowService.java"):
            target = path
            break

    assert target is not None, "未找到 LegacyMegaWorkflowService.java"

    result = parser.extract_with_calls(target)
    methods = result.get("methods", [])
    internal_calls = result.get("internal_calls", [])
    external_calls = result.get("external_calls", [])

    method_names = {m.get("name") for m in methods}

    print("=" * 60)
    print("test_java_ssh 深链路解析验证")
    print("=" * 60)
    print(f"目标文件: {target}")
    print(f"方法数量: {len(methods)}")
    print(f"内部调用数量: {len(internal_calls)}")
    print(f"跨类调用数量: {len(external_calls)}")

    # execute/process/save 三同名方法污染入口
    assert "execute" in method_names
    assert "process" in method_names
    assert "save" in method_names

    # 深链类应该有足够内部调用
    assert len(internal_calls) >= 8, "深链内部调用不足，压测价值不够"
    # 并且要包含跨类调用
    assert len(external_calls) >= 6, "深链跨类调用不足，未形成多层污染"

    print("✅ 深链路与同名污染解析验证通过")


if __name__ == "__main__":
    test_deep_chain_parser_coverage()
