"""
层级树面板 - 左侧可折叠树，点击节点触发图联动
"""
import json
import streamlit as st
from pathlib import Path

LAYER_TREE_PATHS = [
    Path("output/trees/layer_tree.json"),
    Path("output/layer_tree.json"),
]

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


@st.cache_data(ttl=60)
def load_layer_tree() -> dict:
    for path in LAYER_TREE_PATHS:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def render_layer_tree_panel(search_query: str = ""):
    """
    渲染层级树面板。
    点击节点后写入 session_state['selected_class'] / 'selected_method'。
    """
    tree = load_layer_tree()
    layers = tree.get("layers", [])

    if not layers:
        st.warning("⚠️ 未找到 layer_tree.json，请先运行 `python main.py` 生成 output/trees/layer_tree.json")
        return

    q = search_query.strip().lower()

    for layer in layers:
        layer_name = layer["name"]
        raw_classes = layer.get("classes", [])

        # 按类名去重，合并 methods 列表
        seen: dict = {}
        for c in raw_classes:
            name = c["name"]
            if name not in seen:
                seen[name] = dict(c)
            else:
                # 合并方法列表
                existing_methods = seen[name].get("methods", [])
                new_methods = c.get("methods", [])
                merged = list(dict.fromkeys(existing_methods + new_methods))
                seen[name]["methods"] = merged
                seen[name]["method_count"] = len(merged)
        classes = list(seen.values())

        # 搜索过滤
        if q:
            classes = [
                c for c in classes
                if q in c["name"].lower()
                or any(q in m.lower() for m in c.get("methods", []))
            ]
        if not classes:
            continue

        color = LAYER_COLORS.get(layer_name, "#95A5A6")
        badge = (
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:10px;font-size:11px;font-weight:600">'
            f'{layer_name.upper()}</span>'
        )

        # ── 层级标题行：badge + 类数量 + 展开/收起按钮 ──────────────────
        toggle_key = f"layer_open_{layer_name}"
        if toggle_key not in st.session_state:
            st.session_state[toggle_key] = bool(q)
        is_open = st.session_state[toggle_key]

        hdr_col, tog_col = st.columns([11, 1])
        with hdr_col:
            st.markdown(
                f'<div style="padding:6px 0 2px 0;line-height:2;">'
                f'{badge}&nbsp;&nbsp;'
                f'<span style="font-size:13px;color:#444">'
                f'{len(classes)} 个类</span></div>',
                unsafe_allow_html=True,
            )
        with tog_col:
            if st.button(
                "▾" if is_open else "▸",
                key=f"lt_{layer_name}",
                help="展开/收起",
            ):
                st.session_state[toggle_key] = not is_open
                st.rerun()

        # ── 类列表（展开时显示）───────────────────────────────────────
        if is_open:
            for cls in classes:
                class_name = cls["name"]
                method_count = cls.get("method_count", 0)
                methods = cls.get("methods", [])

                is_selected = (
                    st.session_state.get("selected_class") == class_name
                    and st.session_state.get("selected_method") is None
                )

                btn_type = "primary" if is_selected else "secondary"
                icon = "▶ " if is_selected else ""
                if st.button(
                    f"{icon}📦 {class_name}  ({method_count} methods)",
                    key=f"cls_{layer_name}_{class_name}",
                    use_container_width=True,
                    type=btn_type,
                ):
                    st.session_state["selected_class"] = class_name
                    st.session_state["selected_method"] = None
                    st.session_state["selected_layer"] = layer_name
                    st.rerun()

                # 展开方法按钮
                if is_selected or (q and any(q in m.lower() for m in methods)):
                    for method in methods:
                        if q and q not in method.lower() and q not in class_name.lower():
                            continue
                        is_m = (
                            st.session_state.get("selected_class") == class_name
                            and st.session_state.get("selected_method") == method
                        )
                        m_icon = "▶ " if is_m else ""
                        if st.button(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;{m_icon}⚙ {method}",
                            key=f"mth_{layer_name}_{class_name}_{method}",
                            use_container_width=True,
                            type="primary" if is_m else "secondary",
                        ):
                            st.session_state["selected_class"] = class_name
                            st.session_state["selected_method"] = method
                            st.session_state["selected_layer"] = layer_name
                            st.rerun()

        st.markdown(
            '<hr style="margin:6px 0 10px 0;border:none;border-top:1px solid #eee">',
            unsafe_allow_html=True,
        )
