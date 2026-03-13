"""
包结构树面板 - Tab2，按文件路径嵌套展示
"""
import json
import streamlit as st
from pathlib import Path

PACKAGE_TREE_PATHS = [
    Path("output/trees/package_tree.json"),
    Path("output/package_tree.json"),
]


@st.cache_data(ttl=60)
def load_package_tree() -> dict:
    for path in PACKAGE_TREE_PATHS:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def _check_match(node: dict, q: str) -> bool:
    """递归检查节点或子孙是否匹配搜索词"""
    name = node.get("name", "").lower()
    if q in name:
        return True
    if node.get("type") == "class":
        return any(q in m.lower() for m in node.get("methods", []))
    children = node.get("children", {})
    if isinstance(children, dict):
        children = list(children.values())
    return any(_check_match(c, q) for c in children)


def _render_node(node: dict, depth: int = 0, search_query: str = "", parent_path: str = ""):
    """递归渲染包树节点，返回是否渲染了内容"""
    node_type = node.get("type", "package")
    name = node.get("name", "")
    q = search_query.strip().lower()
    node_path = f"{parent_path}/{name}" if parent_path else name

    if node_type == "class":
        if q and not _check_match(node, q):
            return False

        methods = node.get("methods", [])
        method_count = node.get("method_count", len(methods))
        is_selected = (
            st.session_state.get("selected_class") == name
            and st.session_state.get("selected_method") is None
        )

        icon = "▶ " if is_selected else ""
        if st.button(
            f"{icon}📦 {name}  ({method_count} methods)",
            key=f"pkg_cls_{node_path}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state["selected_class"] = name
            st.session_state["selected_method"] = None
            st.rerun()

        # 展开方法列表（选中时或搜索命中时）
        if is_selected or (q and q in name.lower()):
            for method in methods:
                if q and q not in method.lower() and q not in name.lower():
                    continue
                is_m = (
                    st.session_state.get("selected_class") == name
                    and st.session_state.get("selected_method") == method
                )
                m_icon = "▶ " if is_m else ""
                if st.button(
                    f"    {m_icon}⚙ {method}",
                    key=f"pkg_mth_{node_path}_{method}",
                    use_container_width=True,
                    type="primary" if is_m else "secondary",
                ):
                    st.session_state["selected_class"] = name
                    st.session_state["selected_method"] = method
                    st.rerun()
        return True

    else:  # package / root
        children = node.get("children", {})
        if isinstance(children, dict):
            children = list(children.values())

        if q and not any(_check_match(c, q) for c in children):
            return False

        icon = "🗂" if depth == 0 else "📁"
        with st.expander(f"{icon} {name}", expanded=bool(q)):
            for child in sorted(children, key=lambda x: (x.get("type") != "package", x.get("name", ""))):
                _render_node(child, depth + 1, search_query, node_path)
        return True


def render_package_tree_panel(search_query: str = ""):
    """渲染包结构树面板"""
    tree = load_package_tree()
    if not tree:
        st.warning("⚠️ 未找到 package_tree.json，请先运行 `python main.py` 生成 output/trees/package_tree.json")
        return

    root = tree.get("root", {})
    children = root.get("children", {})
    if isinstance(children, dict):
        children = list(children.values())

    # 包在前、类在后排序
    children = sorted(children, key=lambda x: (x.get("type") != "package", x.get("name", "")))

    for child in children:
        _render_node(child, depth=0, search_query=search_query, parent_path=root.get("name", "root"))
