"""
Code-GraphRAG 可视化 Dashboard
启动方式: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Code-GraphRAG Explorer",
    page_icon="🕸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 全局样式
st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 0.5rem; }
    div[data-testid="stButton"] button {
        text-align: left;
        font-size: 12px;
        padding: 3px 8px;
        margin: 1px 0;
        border-radius: 4px;
    }
    div[data-testid="stExpander"] summary p {
        font-weight: 600;
        font-size: 13px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 13px; }
    div[data-testid="column"] { overflow-y: auto; max-height: 80vh; }
</style>
""", unsafe_allow_html=True)

# 初始化 session_state
for key, default in [
    ("selected_class", None),
    ("selected_method", None),
    ("selected_layer", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

from ui.layer_tree_panel import render_layer_tree_panel
from ui.call_graph_panel import render_call_graph_panel, render_detail_bar
from ui.package_tree_panel import render_package_tree_panel

# ── 顶部标题 + 工具栏 ────────────────────────────────────────────
header_col, spacer = st.columns([4, 1])
with header_col:
    st.markdown("### 🕸 Code-GraphRAG Explorer")

toolbar_col1, toolbar_col2, toolbar_col3, toolbar_col4 = st.columns([3, 1, 1, 1])

with toolbar_col1:
    search_query = st.text_input(
        "search",
        placeholder="🔍 搜索类名 / 方法名...",
        label_visibility="collapsed",
        key="search_input",
    )

with toolbar_col2:
    depth = st.select_slider(
        "调用深度",
        options=[1, 2, 3, 4, 5, 6],
        value=3,
        key="depth_slider",
    )

with toolbar_col3:
    direction_label = st.radio(
        "方向",
        ["下游 ↓", "上游 ↑"],
        horizontal=True,
        key="direction_radio",
    )
    direction_key = "downstream" if direction_label.startswith("下") else "upstream"

with toolbar_col4:
    if st.button("🔄 清除选中", use_container_width=True):
        st.session_state["selected_class"] = None
        st.session_state["selected_method"] = None
        st.session_state["selected_layer"] = None
        st.rerun()

st.divider()

# ── 主体：左树 + 右图 ────────────────────────────────────────────
left_col, right_col = st.columns([1, 2], gap="medium")

with left_col:
    tab_layer, tab_pkg = st.tabs(["📐 层级树", "📦 包结构树"])

    with tab_layer:
        render_layer_tree_panel(search_query=search_query)

    with tab_pkg:
        render_package_tree_panel(search_query=search_query)

with right_col:
    selected_class = st.session_state.get("selected_class")
    selected_method = st.session_state.get("selected_method")
    selected_layer = st.session_state.get("selected_layer")

    # 当前选中节点标签
    if selected_class:
        layer_colors = {
            "action": "#E74C3C", "controller": "#E74C3C", "facade": "#E67E22",
            "service": "#27AE60", "biz": "#2980B9", "bl": "#2980B9",
            "dal": "#8E44AD", "dao": "#8E44AD", "model": "#16A085",
            "util": "#7F8C8D", "utils": "#7F8C8D",
        }
        lc = layer_colors.get(selected_layer or "", "#95A5A6")
        badge = (
            f'<span style="background:{lc};color:white;padding:2px 8px;'
            f'border-radius:10px;font-size:11px">{(selected_layer or "").upper()}</span>'
        )
        node_label = f"{selected_class}.{selected_method}" if selected_method else selected_class
        st.markdown(
            f'当前节点: {badge} &nbsp; <code>{node_label}</code>',
            unsafe_allow_html=True,
        )

    # 渲染图，获取点击节点
    clicked_node = render_call_graph_panel(
        class_name=selected_class or "",
        method_name=selected_method or "",
        depth=depth,
        direction=direction_key,
    )

    # 点击图中节点 → 解析并更新选中状态（格式: "ClassName.methodName"）
    if clicked_node and isinstance(clicked_node, str) and "." in clicked_node:
        parts = clicked_node.split(".", 1)
        new_class, new_method = parts[0], parts[1]
        if new_class != selected_class or new_method != selected_method:
            st.session_state["selected_class"] = new_class
            st.session_state["selected_method"] = new_method
            st.rerun()

# ── 底部详情栏 ───────────────────────────────────────────────────
st.divider()
render_detail_bar(
    class_name=st.session_state.get("selected_class") or "",
    method_name=st.session_state.get("selected_method") or "",
)
