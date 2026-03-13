"""
专项测试：验证 test_java_ssh 样例集的扫描与解析覆盖。
"""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.scanner.scanner import scan_java_files
from src.parser.java_parser import JavaParser


def test_ssh_scanner_and_parser():
    project_path = "./fixtures/ssh"
    java_files = scan_java_files(project_path)

    print("=" * 60)
    print("test_java_ssh 扫描与解析验证")
    print("=" * 60)
    print(f"Java 文件数量: {len(java_files)}")

    parser = JavaParser()
    class_count = 0
    method_count = 0
    internal_calls = 0
    external_calls = 0

    for file_path in java_files:
        result = parser.extract_with_calls(file_path)
        class_count += len(result.get("classes", []))
        method_count += len(result.get("methods", []))
        internal_calls += len(result.get("internal_calls", []))
        external_calls += len(result.get("external_calls", []))

    print(f"类数量: {class_count}")
    print(f"方法数量: {method_count}")
    print(f"内部调用数量: {internal_calls}")
    print(f"跨类调用数量: {external_calls}")

    assert len(java_files) >= 35, "test_java_ssh 应至少包含 35 个 Java 文件"
    assert method_count >= 120, "test_java_ssh 方法数量过少，压测价值不足"
    assert external_calls >= 60, "跨类调用数量过少，无法有效压测调用图谱"

    print("✅ test_java_ssh 样例基础校验通过")


if __name__ == "__main__":
    test_ssh_scanner_and_parser()
