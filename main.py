import os
from tqdm import tqdm
from src.config import Config
from src.scanner.scanner import scan_java_files
from src.parser.java_parser import JavaParser
from src.storage.vector_store import KnowledgeBase
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
    all_classes = {}  # file_path -> list of class names
    all_calls = []    # 包含 internal_calls 和 external_calls

    for file_path in tqdm(business_files, desc="解析业务层"):
        result = parser.extract_with_calls(file_path)
        
        classes = result.get('classes', [])
        methods = result.get('methods', [])
        internal_calls = result.get('internal_calls', [])
        external_calls = result.get('external_calls', [])

        # 存储类节点到 Neo4j
        if graph_store and classes:
            all_classes[file_path] = classes
            for class_name in classes:
                graph_store.add_class_node(class_name, file_path)

        # 存储方法节点到 Neo4j
        if graph_store:
            for method in methods:
                graph_store.add_method_node(method['name'], method.get('class_name', ''), file_path)

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

    print(f"✅ 共解析 {len(method_index)} 个业务层方法")
    return method_index, all_calls


def phase2_find_caller_nodes(method_index):
    print("\n🔍 阶段2：分析调用关系（找出调用其他方法最多的方法）...")

    method_names = {m['name'] for m in method_index}
    
    caller_count = {}
    for method in method_index:
        name = method['name']
        code = method['code']
        count = 0
        for mname in method_names:
            if mname != name and mname in code:
                count += 1
        caller_count[name] = count

    hot_nodes = sorted(caller_count.items(), key=lambda x: x[1], reverse=True)[:20]

    print(f"📈 Top 20 调用其他方法最多的方法:")
    for i, (name, count) in enumerate(hot_nodes):
        print(f"  {i+1}. {name} (调用了 {count} 个其他方法)")

    return hot_nodes


def phase3_analyze_hot_nodes(method_index, hot_nodes):
    if not hot_nodes:
        print("✅ 没有需要分析的节点")
        return

    method_map = {m['name']: m for m in method_index}

    print(f"\n🤖 阶段3：调用LLM分析 top5 方法...")

    kb = KnowledgeBase()

    for method_name, degree in hot_nodes[:5]:
        if method_name in method_map:
            method = method_map[method_name]
            code = method['code']
            git_info = {"author": "Unknown", "message": "调用关系分析"}

            from src.llm.processor import LLMProcessor
            summary = LLMProcessor.generate_summary(method_name, code, git_info)

            chunk_id = f"{method['file_path']}_{method_name}".replace(os.sep, "_")
            metadata = {
                "file_path": method['file_path'],
                "method_name": method_name,
                "class_name": method.get('class_name', ''),
                "is_caller_node": True,
                "calls_count": degree
            }

            kb.add_code_chunk(chunk_id, summary, code, metadata)
            print(f"  ✅ {method_name}")

    print(f"✅ 分析完成！已存储 {min(5, len(hot_nodes))} 个方法")


def main():
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
        internal_count = 0
        external_count = 0
        for call in tqdm(all_calls, desc="存储调用关系"):
            try:
                call_type = call.get('type', 'internal')
                caller_class = call.get('caller_class')
                callee_class = call.get('callee_class')
                graph_store.add_call_relationship(
                    call['caller'], 
                    call['callee'],
                    caller_class=caller_class,
                    callee_class=callee_class,
                    call_type=call_type
                )
                if call_type == 'external':
                    external_count += 1
                else:
                    internal_count += 1
            except Exception as e:
                pass  # 忽略单个关系存储失败
        print(f"✅ 调用关系存储完成 (内部: {internal_count}, 跨类: {external_count})")

    # 阶段2：分析热点节点
    hot_nodes = phase2_find_caller_nodes(method_index)

    # 阶段2.5：存储 BELONGS_TO 关系到 Neo4j
    if graph_store:
        print(f"\n📊 存储 {len(method_index)} 个 BELONGS_TO 关系到 Neo4j...")
        for method in tqdm(method_index, desc="存储 BELONGS_TO 关系"):
            try:
                if method['class_name']:
                    graph_store.add_belongs_to_relationship(method['name'], method['class_name'])
            except Exception as e:
                pass
        print("✅ BELONGS_TO 关系存储完成")

    # 阶段3：LLM 分析
    phase3_analyze_hot_nodes(method_index, hot_nodes)

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

    # 关闭图数据库连接
    if graph_store:
        graph_store.close()

    print("\n✨ 完成！")


if __name__ == "__main__":
    main()
