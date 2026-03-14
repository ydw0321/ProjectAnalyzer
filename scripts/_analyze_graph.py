"""临时脚本：分析 Neo4j 中存储的项目图数据"""
import sys, re
from collections import defaultdict
sys.path.insert(0, ".")
from src.storage.graph_store import GraphStore
from src.config import Config

cfg = Config()
gs = GraphStore(cfg.NEO4J_URI, cfg.NEO4J_USER, cfg.NEO4J_PASSWORD)

def q(session, cypher, **params):
    return list(session.run(cypher, **params))

def infer_layer(class_name):
    if not class_name:
        return "unknown"
    n = class_name.upper()
    if n.startswith("BL"):   return "BL(业务逻辑)"
    if n.startswith("UI"):   return "UI(动作层)"
    if n.startswith("DB"):   return "DB(数据层)"
    if n.startswith("DTO"):  return "DTO"
    if n.startswith("VO"):   return "VO"
    if n.startswith("EN") or n.startswith("ENTITY"): return "Entity"
    return "Util/Other"

with gs.driver.session() as s:
    print("=" * 65)
    print("【基础规模】")
    print("  Class 节点    :", q(s, "MATCH (c:Class) RETURN count(c) AS n")[0]["n"])
    print("  Method 节点   :", q(s, "MATCH (m:Method) RETURN count(m) AS n")[0]["n"])
    print("  CALLS 总边    :", q(s, "MATCH ()-[r:CALLS]->() RETURN count(r) AS n")[0]["n"])
    print("  internal      :", q(s, "MATCH ()-[r:CALLS]->(t:Method) WHERE r.type='internal' RETURN count(r) AS n")[0]["n"])
    print("  external(补链):", q(s, "MATCH ()-[r:CALLS]->(t:Method) WHERE r.type='external' RETURN count(r) AS n")[0]["n"])
    ext_unk = q(s, "MATCH ()-[r:CALLS]->(e:ExternalMethod) RETURN count(r) AS n")[0]["n"]
    print("  external_unknown:", ext_unk)
    total_calls = q(s, "MATCH ()-[r:CALLS]->() RETURN count(r) AS n")[0]["n"]
    print(f"  补链率         : {(total_calls - ext_unk)/total_calls*100:.1f}%")

    # ── 按类名前缀推断层级分布 ──────────────────────────────────
    print()
    print("【层级分布（按类名前缀推断）】")
    rows = q(s, "MATCH (m:Method)-[:BELONGS_TO]->(c:Class) RETURN c.name AS cls, count(m) AS cnt")
    layer_classes = defaultdict(int)
    layer_methods = defaultdict(int)
    for r in rows:
        L = infer_layer(r["cls"] or "")
        layer_classes[L] += 1
        layer_methods[L] += r["cnt"]
    for L in sorted(layer_methods, key=layer_methods.get, reverse=True):
        print(f"  {L:20s}  classes={layer_classes[L]:4d}  methods={layer_methods[L]:5d}")

    # ── God Class ─────────────────────────────────────────────────
    print()
    print("【God Class（方法数 > 60）】")
    rows = q(s, """
        MATCH (m:Method)-[:BELONGS_TO]->(c:Class)
        WITH c.name AS cls, count(m) AS cnt
        WHERE cnt > 60
        RETURN cls, cnt ORDER BY cnt DESC LIMIT 20
    """)
    if rows:
        for r in rows:
            print(f"  {(r['cls'] or 'N/A'):55s} {r['cnt']:4d} methods")
    else:
        print("  (无)")

    # ── God Method ────────────────────────────────────────────────
    print()
    print("【God Method（出度 > 150）】")
    rows = q(s, """
        MATCH (m:Method)-[r:CALLS]->()
        WITH m.name AS name, m.class_name AS cls, count(r) AS out_deg
        WHERE out_deg > 150
        RETURN name, cls, out_deg ORDER BY out_deg DESC LIMIT 20
    """)
    if rows:
        for r in rows:
            c = (r['cls'] or '')[:38]
            n = (r['name'] or '')[:28]
            print(f"  {c:38s}.{n:28s}  out={r['out_deg']}")
    else:
        print("  (无)")

    # ── 孤立方法 ──────────────────────────────────────────────────
    print()
    print("【孤立方法（无调用 & 不被调用）】")
    rows = q(s, """
        MATCH (m:Method)
        WHERE NOT (m)-[:CALLS]->() AND NOT ()-[:CALLS]->(m)
        RETURN count(m) AS n
    """)
    print("  孤立方法数:", rows[0]["n"])

    # ── 热点方法（被调 in-degree）─────────────────────────────────
    print()
    print("【被调用最多 Top 20（热点方法）】")
    rows = q(s, """
        MATCH ()-[r:CALLS]->(m:Method)
        WITH m.name AS name, m.class_name AS cls, count(r) AS in_deg
        RETURN name, cls, in_deg ORDER BY in_deg DESC LIMIT 20
    """)
    for r in rows:
        c = (r['cls'] or '')[:38]
        n = (r['name'] or '')[:28]
        print(f"  {c:38s}.{n:28s}  in={r['in_deg']}")

    # ── 跨层调用分析 ───────────────────────────────────────────────
    print()
    print("【跨层调用统计（按类名前缀）】")
    rows = q(s, """
        MATCH (m1:Method)-[:CALLS]->(m2:Method)
        WHERE m1.class_name <> m2.class_name
        RETURN m1.class_name AS from_cls, m2.class_name AS to_cls
        LIMIT 200000
    """)
    cross = defaultdict(int)
    for r in rows:
        fl = infer_layer(r["from_cls"] or "")
        tl = infer_layer(r["to_cls"] or "")
        if fl != tl:
            cross[(fl, tl)] += 1
    for (fl, tl), cnt in sorted(cross.items(), key=lambda x: -x[1])[:15]:
        print(f"  {fl:20s} -> {tl:20s}  {cnt:6d} calls")

    # ── 循环调用 ──────────────────────────────────────────────────
    print()
    print("【直接循环调用（A→B→A）】")
    rows = q(s, """
        MATCH (m1:Method)-[:CALLS]->(m2:Method)-[:CALLS]->(m1)
        WHERE id(m1) < id(m2)
        RETURN m1.class_name + '.' + m1.name AS a,
               m2.class_name + '.' + m2.name AS b
        LIMIT 20
    """)
    print(f"  循环对数: {len(rows)}")
    for r in rows[:10]:
        print(f"  {(r['a'] or '')[:55]}  <->  {(r['b'] or '')[:40]}")

    # ── 残留 external_unknown Top 20 ────────────────────────────
    print()
    print("【残留 external_unknown Top 20（补链失败）】")
    rows = q(s, """
        MATCH (caller:Method)-[:CALLS]->(e:ExternalMethod)
        RETURN e.name AS method_name, count(*) AS cnt
        ORDER BY cnt DESC LIMIT 20
    """)
    for r in rows:
        print(f"  {(r['method_name'] or ''):45s} called {r['cnt']:5d}×")

    # ── 推断边分布 ───────────────────────────────────────────────
    print()
    print("【推断边类型分布】")
    rows = q(s, """
        MATCH ()-[r:CALLS]->(m:Method)
        WHERE r.inferred = true
        RETURN r.inferred_reason AS reason, count(r) AS cnt
        ORDER BY cnt DESC
    """)
    for r in rows[:15]:
        reason = str(r['reason'] or 'N/A')
        # group path_proximity:N
        if reason.startswith("path_proximity"):
            reason = "path_proximity:*"
        else:
            pass
        print(f"  {reason:40s}  {r['cnt']}")

    # ── @Mapper / @Service 识别情况 ──────────────────────────────
    print()
    print("【Spring 注解识别】")
    mapper_cnt = q(s, "MATCH (c:Class {is_mapper:true}) RETURN count(c) AS n")[0]["n"]
    service_cnt = q(s, "MATCH (c:Class {is_service:true}) RETURN count(c) AS n")[0]["n"]
    print(f"  is_mapper=true : {mapper_cnt}")
    print(f"  is_service=true: {service_cnt}")

    # ── 复杂度分布直方图 ──────────────────────────────────────────
    print()
    print("【出度分布直方图（每个方法调用了多少其他方法）】")
    rows = q(s, """
        MATCH (m:Method)
        OPTIONAL MATCH (m)-[r:CALLS]->()
        WITH m, count(r) AS out_deg
        RETURN
          sum(CASE WHEN out_deg = 0 THEN 1 ELSE 0 END) AS d0,
          sum(CASE WHEN out_deg >= 1 AND out_deg <= 5 THEN 1 ELSE 0 END) AS d1_5,
          sum(CASE WHEN out_deg >= 6 AND out_deg <= 20 THEN 1 ELSE 0 END) AS d6_20,
          sum(CASE WHEN out_deg >= 21 AND out_deg <= 50 THEN 1 ELSE 0 END) AS d21_50,
          sum(CASE WHEN out_deg >= 51 AND out_deg <= 100 THEN 1 ELSE 0 END) AS d51_100,
          sum(CASE WHEN out_deg > 100 THEN 1 ELSE 0 END) AS d100p
    """)
    r = rows[0]
    print(f"  出度=0         : {r['d0']:5d} (无任何调用)")
    print(f"  出度 1-5       : {r['d1_5']:5d}")
    print(f"  出度 6-20      : {r['d6_20']:5d}")
    print(f"  出度 21-50     : {r['d21_50']:5d}")
    print(f"  出度 51-100    : {r['d51_100']:5d}")
    print(f"  出度 >100      : {r['d100p']:5d} ← 复杂度极高风险")

gs.close()
print()
print("=" * 65)
print("分析完成")

