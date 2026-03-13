"""
智能问答面板：基于 GraphRAGEngine 提供交互式问答。
"""
import streamlit as st

from src.llm.graphrag import GraphRAGEngine


@st.cache_resource
def get_graphrag_engine() -> GraphRAGEngine:
    return GraphRAGEngine()


def _init_chat_state():
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "chat_prefill" not in st.session_state:
        st.session_state["chat_prefill"] = ""


def render_chat_panel(selected_class: str = "", selected_method: str = ""):
    _init_chat_state()
    engine = get_graphrag_engine()

    anchor = ""
    if selected_class and selected_method:
        anchor = f"{selected_class}.{selected_method}"
    elif selected_class:
        anchor = selected_class

    col1, col2 = st.columns([4, 1])
    with col1:
        if anchor:
            st.caption(f"当前焦点节点: {anchor}")
        else:
            st.caption("当前未聚焦节点，将按全局语义检索回答")

    with col2:
        if st.button("清空对话", use_container_width=True):
            st.session_state["chat_history"] = []
            st.rerun()

    if anchor and st.session_state.get("chat_prefill") == "":
        st.session_state["chat_prefill"] = f"请分析 {anchor} 的业务职责和上下游调用链"

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            refs = msg.get("refs")
            if refs:
                with st.expander("引用的方法", expanded=False):
                    for ref in refs:
                        st.write(f"- {ref}")

    question = st.chat_input("输入你的问题，例如：订单创建流程是怎样的？")
    if not question:
        if st.session_state.get("chat_prefill"):
            st.info(f"建议问题: {st.session_state['chat_prefill']}")
        return

    st.session_state["chat_history"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在检索图与向量上下文..."):
            result = engine.query(
                question=question,
                selected_class=selected_class or None,
                selected_method=selected_method or None,
                n_results=10,
            )
            answer = result.get("answer", "")
            refs = result.get("refs", [])
            st.markdown(answer)
            if refs:
                with st.expander("引用的方法", expanded=False):
                    for ref in refs:
                        st.write(f"- {ref}")

    st.session_state["chat_history"].append(
        {
            "role": "assistant",
            "content": answer,
            "refs": refs,
        }
    )
    st.session_state["chat_prefill"] = ""
