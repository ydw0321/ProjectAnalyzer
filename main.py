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
    method_signature_index = {}
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
                    'file_path': file_path,
                    'param_count': method.get('param_count', 0),
                })

        # 收集调用关系（包括内部和外部）
        all_calls.extend(internal_calls)
        all_calls.extend(external_calls)

        for method in methods:
            class_name = method.get('class_name', '')
            method_name = method.get('name', '')
            param_count = method.get('param_count', 0)
            if class_name and method_name:
                key = (class_name, method_name)
                method_signature_index.setdefault(key, set()).add(param_count)

            method_index.append({
                'name': method_name,
                'class_name': class_name,
                'param_count': param_count,
                'file_path': file_path,
                'code': method['code'],
            })

    if graph_store:
        graph_store.batch_add_class_nodes(class_nodes)
        graph_store.batch_add_method_nodes(method_nodes)

    print(f"✅ 共解析 {len(method_index)} 个业务层方法")
    return method_index, all_calls, method_signature_index


def phase2_collect_call_stats(method_index, all_calls):
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

    return hot_nodes, dict(caller_count)


def phase3_index_all(method_index, hot_nodes, call_counts, index_all: bool = False, index_top: int = 0):
    """阶段3：LLM 摘要索引。
    index_all=True  → 全量索引所有方法（增量跳过已有）
    index_all=False → 仅索引 top-5 热点方法（快速模式，保持向后兼容）
    """
    # 延迟导入，确保 graph-only 模式不触发向量和 LLM 依赖
    from src.storage.vector_store import KnowledgeBase
    from src.llm.batch_indexer import BatchIndexer
    from src.llm.processor import LLMProcessor

    kb = KnowledgeBase()
    index_top = max(0, index_top or 0)

    if index_all:
        workers = max(1, Config.LLM_INDEX_MAX_WORKERS)
        target = f"前 {index_top} 个方法" if index_top > 0 else f"{len(method_index)} 个方法"
        print(
            f"\n🤖 阶段3：全量 LLM 摘要索引（目标={target}，增量更新，并发={workers}）..."
        )
        indexer = BatchIndexer(knowledge_base=kb)
        stats = indexer.index_all(
            method_index,
            call_counts=call_counts,
            top_n=index_top if index_top > 0 else None,
            max_workers=workers,
            skip_existing=True,
        )
        print(
            f"✅ 全量索引完成：总计 {stats['total']}，"
            f"新增 {stats['indexed']}，跳过 {stats['skipped']}，失败 {stats['failed']}"
        )
        print(f"   向量库当前文档数：{kb.count()}")
    else:
        ranked_methods = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)
        if not ranked_methods:
            print("✅ 没有需要分析的节点")
            return
        method_map = {
            f"{m.get('class_name', '')}.{m['name']}".strip('.'): m for m in method_index
        }
        top_k = index_top if index_top > 0 else 5
        print(f"\n🤖 阶段3：调用LLM分析 top{top_k} 热点方法...")
        for method_key, degree in ranked_methods[:top_k]:
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
        print(f"✅ 分析完成！已存储 {min(top_k, len(ranked_methods))} 个方法")


def main(run_neo4j=True, run_vector=True, index_all=False, index_top=0, reset_graph=False):
    setup_logging()
    print("🚀 Code-GraphRAG 构建流水线\n")

    if not run_neo4j and not run_vector:
        print("⚠️ 未选择任何执行阶段，请设置 --neo4j-only 或 --vector-only，或不设置以执行全流程。")
        return

    # 初始化图数据库（可选）
    graph_store = None
    if run_neo4j:
        try:
            graph_store = GraphStore()
            print("✅ Neo4j 连接成功")
            if reset_graph:
                print("🧹 已启用图重置：清空 Neo4j 旧数据...")
                graph_store.clear_graph()
                print("✅ Neo4j 图数据已清空")
        except Exception as e:
            print(f"⚠️ Neo4j 连接失败: {e}")
    elif reset_graph:
        print("⚠️ 已忽略 --reset-graph（当前未执行 Neo4j 阶段）")

    # 阶段1：解析源码（按模式可选写入 Neo4j）
    method_index, all_calls, method_signature_index = phase1_parse_and_index(graph_store)

    # 阶段1.5：存储调用关系到 Neo4j
    if run_neo4j and graph_store and all_calls:
        print(f"\n📊 存储 {len(all_calls)} 条调用关系到 Neo4j...")
        call_stats = graph_store.batch_add_call_relationships(
            all_calls,
            signature_index=method_signature_index,
        )
        internal_count = sum(1 for c in all_calls if c.get('type') == 'internal')
        external_count = sum(1 for c in all_calls if c.get('type') == 'external')
        print(f"✅ 调用关系存储完成 (内部: {internal_count}, 跨类: {external_count})")
        print(
            "📈 匹配统计: "
            f"精确命中={call_stats.get('signature_exact_hits', 0)}, "
            f"唯一回退={call_stats.get('unique_fallback_hits', 0)}, "
            f"转unknown={call_stats.get('unmatched_to_unknown', 0)}, "
            f"内部丢弃={call_stats.get('internal_unmatched_dropped', 0)}"
        )
        print(
            "📈 样本统计: "
            f"总行={call_stats.get('total_rows', 0)}, "
            f"去重后={call_stats.get('deduplicated_rows', 0)}, "
            f"内部={call_stats.get('internal_rows', 0)}, "
            f"外部已知={call_stats.get('external_rows', 0)}, "
            f"外部未知={call_stats.get('direct_unknown_rows', 0)}"
        )

        resolved_unknown = graph_store.resolve_external_unknown_calls()
        print(f"✅ external_unknown 自动补链完成 (补链: {resolved_unknown})")

    # 阶段2：分析热点节点
    hot_nodes, call_counts = phase2_collect_call_stats(method_index, all_calls)

    # 阶段2.5：存储 BELONGS_TO 关系到 Neo4j
    if run_neo4j and graph_store:
        print(f"\n📊 存储 {len(method_index)} 个 BELONGS_TO 关系到 Neo4j...")
        belongs_to_rows = [
            {
                'method_name': method['name'],
                'class_name': method['class_name'],
                'file_path': method['file_path'],
                'param_count': method.get('param_count', 0),
            }
            for method in method_index if method.get('class_name')
        ]
        graph_store.batch_add_belongs_to_relationships(belongs_to_rows)
        print("✅ BELONGS_TO 关系存储完成")

    # 阶段3：LLM 摘要索引（可选）
    if run_vector:
        phase3_index_all(
            method_index,
            hot_nodes,
            call_counts,
            index_all=index_all,
            index_top=index_top,
        )
    else:
        print("\n⏭️ 阶段3已跳过（当前仅执行 Neo4j 阶段）")

    # 阶段4：构建层级节点并生成架构树
    if run_neo4j and graph_store:
        print("\n📊 阶段4：构建层级节点...")
        try:
            # 构建 Layer 节点
            graph_store.build_layer_nodes_from_classes()
            print("✅ Layer 节点构建完成")

            # 生成架构树并导出
            with ArchitectureTreeGenerator() as tree_gen:
                # 层级树
                layer_tree = tree_gen.generate_layer_tree("Project")
                tree_gen.export_tree_json(layer_tree, "output/trees/layer_tree.json")
                tree_gen.export_mermaid(layer_tree, "output/trees/layer_tree.md")

                # 包结构树
                package_tree = tree_gen.generate_package_tree("Project")
                tree_gen.export_tree_json(package_tree, "output/trees/package_tree.json")

                # 调用链树
                chain_tree = tree_gen.generate_call_chain_tree()
                tree_gen.export_tree_json(chain_tree, "output/trees/call_chain_tree.json")
                tree_gen.export_plantuml(chain_tree, "output/trees/call_chain_tree.puml")

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
        help="仅执行 Neo4j 图存储与树生成（兼容旧参数，等价于 --neo4j-only）",
    )
    parser.add_argument(
        "--neo4j-only",
        action="store_true",
        help="仅执行 Neo4j 图存储与树生成，跳过向量和 LLM 摘要",
    )
    parser.add_argument(
        "--vector-only",
        action="store_true",
        help="仅执行向量摘要索引，不写入 Neo4j；可反复执行增量补齐未索引方法",
    )
    parser.add_argument(
        "--index-all",
        action="store_true",
        help="全量 LLM 摘要索引所有方法（增量更新，跳过已有），默认仅索引 top-5",
    )
    parser.add_argument(
        "--index-top",
        type=int,
        default=0,
        help="限制向量索引规模：仅处理前 N 个热点方法（0 表示不限制）",
    )
    parser.add_argument(
        "--reset-graph",
        action="store_true",
        help="执行前清空 Neo4j 图数据，避免不同样本集运行结果累积",
    )
    args = parser.parse_args()

    if args.neo4j_only and args.vector_only:
        parser.error("--neo4j-only 与 --vector-only 不能同时使用")

    run_neo4j = args.neo4j_only or args.graph_only
    run_vector = args.vector_only
    if not run_neo4j and not run_vector:
        run_neo4j = True
        run_vector = True

    main(
        run_neo4j=run_neo4j,
        run_vector=run_vector,
        index_all=args.index_all,
        index_top=args.index_top,
        reset_graph=args.reset_graph,
    )
