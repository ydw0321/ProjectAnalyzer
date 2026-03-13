from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.storage.graph_store import GraphStore


def test_neo4j_storage():
    """测试 Neo4j 图数据库存储"""
    print("🧪 开始 Neo4j 数据验证测试\n")
    
    try:
        with GraphStore() as gs:
            print("✅ Neo4j 连接成功!")
            
            # 统计节点和关系数量
            method_count = gs.get_method_count()
            call_count = gs.get_call_count()
            
            print(f"\n📊 图数据库统计:")
            print(f"  - 方法节点数量: {method_count}")
            print(f"  - 调用关系数量: {call_count}")
            
            # 查询热点节点
            print(f"\n🔥 Top 10 被调用最多的方法:")
            hot_nodes = gs.get_hot_nodes(limit=10)
            if hot_nodes:
                for i, node in enumerate(hot_nodes, 1):
                    print(f"  {i}. {node.get('method_name', 'N/A')} (被调用 {node.get('degree', 0)} 次)")
            else:
                print("  (暂无数据)")
            
            # 验证 Class 节点
            print(f"\n📂 Class 节点查询 (前5个):")
            with gs.driver.session() as session:
                result = session.run("MATCH (c:Class) RETURN c.name as name, c.file_path as file_path LIMIT 5")
                classes = list(result)
                if classes:
                    for c in classes:
                        print(f"  - {c['name']} (@ {c['file_path']})")
                else:
                    print("  (暂无数据)")
            
            # 验证 Method 节点
            print(f"\n🔧 Method 节点查询 (前5个):")
            with gs.driver.session() as session:
                result = session.run("MATCH (m:Method) RETURN m.name as name, m.class_name as class_name LIMIT 5")
                methods = list(result)
                if methods:
                    for m in methods:
                        print(f"  - {m['name']} (属于 {m['class_name']})")
                else:
                    print("  (暂无数据)")
            
            # 验证 BELONGS_TO 关系
            print(f"\n🔗 BELONGS_TO 关系查询 (前5个):")
            with gs.driver.session() as session:
                result = session.run("""
                    MATCH (m:Method)-[:BELONGS_TO]->(c:Class) 
                    RETURN m.name as method_name, c.name as class_name 
                    LIMIT 5
                """)
                relations = list(result)
                if relations:
                    for r in relations:
                        print(f"  - {r['method_name']} -> {r['class_name']}")
                else:
                    print("  (暂无数据)")
            
            # 验证 CALLS 关系
            print(f"\n📞 CALLS 关系查询 (前5个):")
            with gs.driver.session() as session:
                result = session.run("""
                    MATCH (caller:Method)-[:CALLS]->(callee:Method) 
                    RETURN caller.name as caller, callee.name as callee 
                    LIMIT 5
                """)
                calls = list(result)
                if calls:
                    for c in calls:
                        print(f"  - {c['caller']} -> {c['callee']}")
                else:
                    print("  (暂无数据)")
            
            print("\n✅ 数据验证测试完成!")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_neo4j_storage()
