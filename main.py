import os
from tqdm import tqdm
from src.config import Config
from src.git_analyzer.analyzer import GitAnalyzer
from src.parser.java_parser import JavaParser
from src.llm.processor import LLMProcessor
from src.storage.vector_store import KnowledgeBase
from src.scanner.scanner import scan_java_files


def main():
    print("🚀 启动 Code-GraphRAG 构建流水线...")

    git_analyzer = GitAnalyzer(Config.PROJECT_PATH)
    parser = JavaParser()
    kb = KnowledgeBase()

    java_files = scan_java_files(Config.PROJECT_PATH)
    print(f"📂 发现 {len(java_files)} 个 Java 源文件，开始解析...")

    for file_path in tqdm(java_files, desc="解析 Java 文件"):
        git_info = git_analyzer.get_file_last_commit(file_path)
        methods = parser.extract_methods(file_path)

        for method in methods:
            chunk_id = file_path.replace(os.sep, "_").replace("/", "_").replace("\\", "_") + "_" + method['name']
            summary = LLMProcessor.generate_summary(method['name'], method['code'], git_info)

            metadata = {
                "file_path": file_path,
                "method_name": method['name'],
                "git_author": git_info.get("author", "Unknown"),
                "git_message": git_info.get("message", "Unknown"),
                "git_date": git_info.get("date", "Unknown")
            }

            kb.add_code_chunk(chunk_id, summary, method['code'], metadata)

    print(f"✅ 知识库构建完成！数据已持久化至: {Config.CHROMA_DB_PATH}")


if __name__ == "__main__":
    main()
