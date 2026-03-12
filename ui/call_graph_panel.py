"""
调用链图面板 - 右侧 agraph 交互网络图，实时查询 Neo4j
"""
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from src.tree.query_service import GraphQueryService

LAYER_COLORS = {
    "action":     "#E74C3C",
    "controller": "#E74C3C",
    "facade":     "#E67E22",
    "service":    "#27AE60",
    "biz":        "#2980B9",
    "bl":         "#2980B9",
    "dal":        "#8E44AD",
    "dao":        "#8E44AD",
    "model":      "#16A085",
    "entity":     "#16A085",
    "util":       "#7F8C8D",
    "utils":      "#7F8C8D",
}

CALL_TYPE_COLORS = {
    "internal":         "#2ECC71",
    "external":         "#F39C12",
    "external_unknown": "#E74C3C",
}

CALL_TYPE_DASH = {
    "internal":         False,
    "external":         False,
    "external_unknown": True,
}


@st.cache_resource
def get_query_service() -> GraphQueryService:
    return GraphQueryService()


@st.cache_data(ttl=30)
def load_class_layer_map() -> dict:
    """加载所有类的层级映射（带缓存）"""
    qs = get_query_service()
    stats = qs.get_layer_statistics()
    result = {}
    for layer_info in stats:
        for cls in layer_info.get("classes", []):
            result[cls] = layer_info["layer"]
    return result


def _node_color(class_name: str, class_layer_map: dict) -> str:
    layer = class_layer_map.get(class_name, "unknown")
    return LAYER_COLORS.get(layer, "#BDC3C7")


def render_call_graph_panel(
    class_name: str,
    method_name: str,
    depth: int,
    direction: str = "downstream",
):
    """
    渲染调用链交互图。
    返回用户在图中点击的节点 ID（字符串），否则返回 None。
    """
    if not class_name:
        st.markdown(
            "<div style='text-align:center;color:#888;padding:120px 0'>"
            "👈 请在左侧点击一个类或方法，查看其调用链图"
            "</div>",
            unsafe_allow_html=True,
        )
        return None

    qs = get_query_service()
    class_layer_map = load_class_layer_map()

    display_target = f"{class_name}.{method_name}" if method_name else class_name

    with st.spinner(f"查询 {display_target} 的{'下游' if direction=='downstream' else '上游'}调用链 (深度={depth})..."):
        try:
            if direction == "downstream":
                raw = qs.get_downstream_calls(method_name or "", class_name, max_depth=depth)
            else:
                raw = qs.get_upstream_callers(method_name or "", class_name, max_depth=depth)
        except Exception as e:
            st.error(f"Neo4j 查询失败: {e}")
            return None

    # ── 构建节点和边 ──────────────────────────────────────────────
    nodes_map: dict[str, Node] = {}
    edges: list[Edge] = []

    # 根节点（当前选中）
    root_id = display_target
    root_color = _node_color(class_name, class_layer_map)
    nodes_map[root_id] = Node(
        id=root_id,
        label=f"{method_name or class_name}\n({class_name})" if method_name else class_name,
        size=28,
        color=root_color,
        borderWidth=3,
        borderWidthSelected=4,
        shape="dot",
        font={"size": 13, "bold": True, "color": "#ffffff"},
    )

    for item in raw:
        callee_name = item.get("method") or ""
        callee_class = item.get("class") or "external"
        call_type = item.get("call_type", "external_unknown")
        caller_name = item.get("caller") or (method_name or class_name)

        if direction == "downstream":
            src_class = class_name
            src_method = caller_name
            tgt_class = callee_class
            tgt_method = callee_name
        else:
            src_class = callee_class
            src_method = callee_name
            tgt_class = class_name
            tgt_method = caller_name

        source_id = f"{src_class}.{src_method}" if src_method else src_class
        target_id = f"{tgt_class}.{tgt_method}" if tgt_method else tgt_class

        for nid, nc, nm in [(source_id, src_class, src_method), (target_id, tgt_class, tgt_method)]:
            if nid not in nodes_map:
                color = _node_color(nc, class_layer_map)
                label = f"{nm}\n({nc})" if nm and nc else (nm or nc)
                nodes_map[nid] = Node(
                    id=nid,
                    label=label,
                    size=20,
                    color=color,
                    shape="dot",
                    font={"size": 11, "color": "#ffffff"},
                )

        edge_color = CALL_TYPE_COLORS.get(call_type, "#BDC3C7")
        edges.append(
            Edge(
                source=source_id,
                target=target_id,
                color=edge_color,
                dashes=CALL_TYPE_DASH.get(call_type, False),
                width=2.5 if call_type == "internal" else 1.5,
                smooth={"type": "curvedCW", "roundness": 0.1},
            )
        )

    if len(nodes_map) <= 1:
        st.info(
            f"🔍 **{display_target}** 没有{'下游调用' if direction == 'downstream' else '上游调用者'}（深度={depth}）"
        )
        if nodes_map:
            agraph(nodes=list(nodes_map.values()), edges=[], config=Config(width="100%", height=200, directed=True, physics=False))
        return None

    # ── 图例 ──────────────────────────────────────────────────────
    legend_cols = st.columns(7)
    legends = [
        ("action/ctrl", "#E74C3C"), ("facade", "#E67E22"),
        ("service", "#27AE60"), ("biz", "#2980B9"),
        ("dal/dao", "#8E44AD"), ("model", "#16A085"), ("util", "#7F8C8D"),
    ]
    for col, (name, color) in zip(legend_cols, legends):
        col.markdown(
            f'<span style="background:{color};color:white;padding:2px 6px;'
            f'border-radius:4px;font-size:11px">{name}</span>',
            unsafe_allow_html=True,
        )

    # agraph 配置
    config = Config(
        width="100%",
        height=500,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700",
        collapsible=False,
        node={"labelProperty": "label", "renderLabel": True},
        link={"renderLabel": False},
    )

    clicked = agraph(nodes=list(nodes_map.values()), edges=edges, config=config)

    # 节点数统计
    st.caption(f"共 {len(nodes_map)} 个节点，{len(edges)} 条调用边  |  点击节点可切换焦点")

    return clicked


def render_detail_bar(class_name: str, method_name: str):
    """渲染底部详情栏"""
    if not class_name:
        st.caption("未选中任何节点")
        return

    qs = get_query_service()
    class_layer_map = load_class_layer_map()
    layer = class_layer_map.get(class_name, "unknown")
    color = LAYER_COLORS.get(layer, "#95A5A6")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(
        f'**类**<br><span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:13px">{class_name}</span>',
        unsafe_allow_html=True,
    )
    col2.metric("层级", layer.upper())
    col3.metric("方法", method_name or "（类级别）")

    try:
        downstream = qs.get_downstream_calls(method_name or "", class_name, max_depth=1)
        upstream = qs.get_upstream_callers(method_name or "", class_name, max_depth=1)
        col4.metric("下游调用数", len(downstream))
        col5.metric("上游调用者", len(upstream))
    except Exception:
        col4.metric("下游调用数", "—")
        col5.metric("上游调用者", "—")
