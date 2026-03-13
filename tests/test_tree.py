"""
测试架构树生成器
"""
from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import json
from src.tree import ArchitectureTreeGenerator, GraphQueryService


def test_tree_generator():
    """测试树生成器"""
    print("=" * 50)
    print("测试架构树生成器")
    print("=" * 50)
    
    with ArchitectureTreeGenerator() as generator:
        # 1. 测试层级树生成
        print("\n📊 测试1: 生成层级架构树")
        layer_tree = generator.generate_layer_tree("OrderSystem")
        print(json.dumps(layer_tree, ensure_ascii=False, indent=2)[:1000])
        
        # 2. 测试包结构树
        print("\n📊 测试2: 生成包结构树")
        package_tree = generator.generate_package_tree("OrderSystem")
        print(json.dumps(package_tree, ensure_ascii=False, indent=2)[:1000])
        
        # 3. 测试调用链树
        print("\n📊 测试3: 生成调用链树")
        chain_tree = generator.generate_call_chain_tree()
        print(json.dumps(chain_tree, ensure_ascii=False, indent=2)[:1000])
        
        # 4. 测试汇总信息
        print("\n📊 测试4: 获取汇总信息")
        summary = generator.get_tree_summary()
        print(summary)
        
        # 5. 测试导出 Mermaid
        print("\n📊 测试5: 导出 Mermaid 格式")
        mermaid_code = generator.export_mermaid(layer_tree)
        print(mermaid_code)


def test_query_service():
    """测试图查询服务"""
    print("=" * 50)
    print("测试图查询服务")
    print("=" * 50)
    
    with GraphQueryService() as query:
        # 1. 层级统计
        print("\n📊 层级统计:")
        stats = query.get_layer_statistics()
        for s in stats:
            print(f"  {s['layer']}: {s['class_count']} 个类")
        
        # 2. 入口方法
        print("\n📊 入口方法 (Controller层):")
        entry_methods = query.get_entry_methods()
        for m in entry_methods[:5]:
            print(f"  {m['method_name']} ({m['class_name']})")
        
        # 3. 调用统计
        print("\n📊 调用关系统计:")
        call_stats = query.get_call_statistics()
        print(f"  内部调用: {call_stats['internal']}")
        print(f"  外部调用: {call_stats['external']}")
        print(f"  未知调用: {call_stats['external_unknown']}")
        
        # 4. 测试调用链查询
        if entry_methods:
            test_method = entry_methods[0]['method_name']
            test_class = entry_methods[0].get('class_name')
            
            print(f"\n📊 下游调用链 ({test_method}):")
            downstream = query.get_downstream_calls(test_method, test_class, max_depth=3)
            for d in downstream[:10]:
                print(f"  [{d['depth']}] {d['class']}.{d['method']} ({d['call_type']})")


if __name__ == "__main__":
    try:
        test_query_service()
        test_tree_generator()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
