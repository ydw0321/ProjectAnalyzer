import os
import argparse
import sys
from collections import defaultdict
from tqdm import tqdm
from src.logging_utils import setup_logging
from src.config import Config
from src.scanner.scanner import scan_java_files
from src.parser.java_parser import JavaParser
from src.storage.graph_store import GraphStore
from src.tree import ArchitectureTreeGenerator

def is_business_layer(file_path: str) -> bool:
    # 分析所有 Java 文件，不过滤业务层
    return True


def phase1_parse_and_index(graph_store=None):
    """解析业务层并可选地存储到图数据库"""
    print("📊 阶段1：解析业务层...")

    parser = JavaParser()
    java_files = scan_java_files(Config.PROJECT_PATH)
    
    business_files = [f for f in java_files if is_business_layer(f)]
    print(f"📂 业务层文件: {len(business_files)} 个")

    method_index = []
    all_calls = []    # 包含 internal_calls 和 external_calls
    class_nodes = []
    method_nodes = []

    for file_path in tqdm(business_files, desc="解析业务层"):
        result = parser.extract_with_calls(file_path)
        
        classes = result.get('classes', [])
        methods = result.get('methods', [])
        internal_calls = result.get('internal_calls', [])
        external_calls = result.get('external_calls', [])

        # 收集类节点到 Neo4j
        if graph_store and classes:
            for class_name in classes:
                class_nodes.append({'name': class_name, 'file_path': file_path})

        # 收集方法节点到 Neo4j
        if graph_store:
            for method in methods:
                method_nodes.append({
                    'name': method['name'],
                    'class_name': method.get('class_name', ''),
                    'file_path': file_path
                })

        # 收集调用关系（包括内部和外部）
        all_calls.extend(internal_calls)
        all_calls.extend(external_calls)

        for method in methods:
            method_index.append({
                'name': method['name'],
                'class_name': method.get('class_name', ''),
                'file_path': file_path,
                'code': method['code'],
            })

    if graph_store:
        graph_store.batch_add_class_nodes(class_nodes)
        graph_store.batch_add_method_nodes(method_nodes)

    print(f"✅ 共解析 {len(method_index)} 个业务层方法")
    return method_index, all_calls


def phase2_find_caller_nodes(method_index, all_calls):
    print("\n🔍 阶段2：分析调用关系（基于解析结果统计热点方法）...")

    # 以 Class.method 作为唯一键，避免同名方法互相覆盖
    caller_count = defaultdict(int)
    for call in all_calls:
        caller_class = call.get('caller_class', '')
        caller_name = call.get('caller', '')
        if caller_name:
            key = f"{caller_class}.{caller_name}" if caller_class else caller_name
            caller_count[key] += 1

    # 补齐未出现在调用边中的方法，保证排序输出完整
    for method in method_index:
        key = f"{method.get('class_name', '')}.{method['name']}".strip('.')
        caller_count.setdefault(key, 0)

    hot_nodes = sorted(caller_count.items(), key=lambda x: x[1], reverse=True)[:20]

    print(f"📈 Top 20 调用其他方法最多的方法:")
    for i, (name, count) in enumerate(hot_nodes):
        print(f"  {i+1}. {name} (调用了 {count} 个其他方法)")

    return hot_nodes


def phase3_index_all(method_index, hot_nodes, index_all: bool = False):
    """阶段3：LLM 摘要索引。
    index_all=True  → 全量索引所有方法（增量跳过已有）
    index_all=False → 仅索引 top-5 热点方法（快速模式，保持向后兼容）
    """
    # 延迟导入，确保 graph-only 模式不触发向量和 LLM 依赖
    from src.storage.vector_store import KnowledgeBase
    from src.llm.batch_indexer import BatchIndexer
    from src.llm.processor import LLMProcessor

    kb = KnowledgeBase()

    if index_all:
        print(f"\n🤖 阶段3：全量 LLM 摘要索引（{len(method_index)} 个方法，增量更新）...")
        # 构建调用计数 map（用于写元数据）
        call_counts = {name: count for name, count in hot_nodes}
        indexer = BatchIndexer(knowledge_base=kb)
        stats = indexer.index_all(
            method_index,
            call_counts=call_counts,
            max_workers=4,
            skip_existing=True,
        )
        print(
            f"✅ 全量索引完成：总计 {stats['total']}，"
            f"新增 {stats['indexed']}，跳过 {stats['skipped']}，失败 {stats['failed']}"
        )
        print(f"   向量库当前文档数：{kb.count()}")
    else:
        if not hot_nodes:
            print("✅ 没有需要分析的节点")
            return
        method_map = {
            f"{m.get('class_name', '')}.{m['name']}".strip('.'): m for m in method_index
        }
        print(f"\n🤖 阶段3：调用LLM分析 top5 热点方法...")
        for method_key, degree in hot_nodes[:5]:
            if method_key in method_map:
                method = method_map[method_key]
                method_name = method['name']
                git_info = {"author": "Unknown", "message": "调用关系分析"}
                summary = LLMProcessor.generate_summary(
                    method_name=method_name,
                    code=method['code'],
                    git_info=git_info,
                    class_name=method.get('class_name', ''),
                )
                chunk_id = (
                    f"{method['file_path']}::{method.get('class_name', '')}::{method_name}"
                    .replace(os.sep, "/")
                )
                metadata = {
                    "file_path": method['file_path'],
                    "method_name": method_name,
                    "class_name": method.get('class_name', ''),
                    "layer": "unknown",
                    "call_count": degree,
                    "callers_count": 0,
                }
                kb.add_code_chunk(chunk_id, summary, method['code'], metadata)
                print(f"  ✅ {method_key}")
        print(f"✅ 分析完成！已存储 {min(5, len(hot_nodes))} 个方法")


def main(enable_llm=True, index_all=False):
    setup_logging()
    print("🚀 Code-GraphRAG 构建流水线\n")

    # 初始化图数据库（可选）
    graph_store = None
    try:
        graph_store = GraphStore()
        print("✅ Neo4j 连接成功")
    except Exception as e:
        print(f"⚠️ Neo4j 连接失败: {e}")

    # 阶段1：解析并存储到图数据库
    method_index, all_calls = phase1_parse_and_index(graph_store)

    # 阶段1.5：存储调用关系到 Neo4j
    if graph_store and all_calls:
        print(f"\n📊 存储 {len(all_calls)} 条调用关系到 Neo4j...")
        graph_store.batch_add_call_relationships(all_calls)
        internal_count = sum(1 for c in all_calls if c.get('type') == 'internal')
        external_count = sum(1 for c in all_calls if c.get('type') == 'external')
        print(f"✅ 调用关系存储完成 (内部: {internal_count}, 跨类: {external_count})")

        resolved_unknown = graph_store.resolve_external_unknown_calls()
        print(f"✅ external_unknown 自动补链完成 (补链: {resolved_unknown})")

    # 阶段2：分析热点节点
    hot_nodes = phase2_find_caller_nodes(method_index, all_calls)

    # 阶段2.5：存储 BELONGS_TO 关系到 Neo4j
    if graph_store:
        print(f"\n📊 存储 {len(method_index)} 个 BELONGS_TO 关系到 Neo4j...")
        belongs_to_rows = [
            {'method_name': method['name'], 'class_name': method['class_name']}
            for method in method_index if method.get('class_name')
        ]
        graph_store.batch_add_belongs_to_relationships(belongs_to_rows)
        print("✅ BELONGS_TO 关系存储完成")

    # 阶段3：LLM 摘要索引（可选）
    if enable_llm:
        phase3_index_all(method_index, hot_nodes, index_all=index_all)
    else:
        print("\n⏭️ 阶段3已跳过（graph-only 模式）")

    # 阶段4：构建层级节点并生成架构树
    if graph_store:
        print("\n📊 阶段4：构建层级节点...")
        try:
            # 构建 Layer 节点
            graph_store.build_layer_nodes_from_classes()
            print("✅ Layer 节点构建完成")

            # 生成架构树并导出
            with ArchitectureTreeGenerator() as tree_gen:
                # 层级树
                layer_tree = tree_gen.generate_layer_tree("Project")
                tree_gen.export_tree_json(layer_tree, "output/layer_tree.json")
                tree_gen.export_mermaid(layer_tree, "output/layer_tree.md")

                # 包结构树
                package_tree = tree_gen.generate_package_tree("Project")
                tree_gen.export_tree_json(package_tree, "output/package_tree.json")

                # 调用链树
                chain_tree = tree_gen.generate_call_chain_tree()
                tree_gen.export_tree_json(chain_tree, "output/call_chain_tree.json")
                tree_gen.export_plantuml(chain_tree, "output/call_chain_tree.puml")

                # 打印汇总
                print(tree_gen.get_tree_summary())

            print("✅ 架构树导出完成 (output/ 目录)")
        except Exception as e:
            print(f"⚠️ 架构树生成失败: {e}")
            if graph_store:
                graph_store.close()
            sys.exit(1)

    # 关闭图数据库连接
    if graph_store:
        graph_store.close()

    print("\n✨ 完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code-GraphRAG pipeline")
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="仅执行图存储与树生成流程，跳过向量和 LLM 分析",
    )
    parser.add_argument(
        "--index-all",
        action="store_true",
        help="全量 LLM 摘要索引所有方法（增量更新，跳过已有），默认仅索引 top-5",
    )
    args = parser.parse_args()

    main(enable_llm=not args.graph_only, index_all=args.index_all)
