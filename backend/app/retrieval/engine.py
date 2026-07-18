"""Outer graph của Retrieval Engine: normalize -> rewrite -> react subgraph -> rerank.

react subgraph (langgraph.prebuilt.create_react_agent) là phần agentic thật — model tự
quyết định gọi query_vector_store/query_graph_knowledge khi nào, mấy lần. normalize/
rewrite/rerank là node deterministic bọc quanh, luôn chạy đúng 1 lần (xem lý do trong
kế hoạch — tránh phó mặc hoàn toàn cho ReAct loop với domain nghiệp vụ ngân hàng).

Lưu ý: `create_react_agent` đã deprecated từ langgraph 1.0 (thay bằng
`langchain.agents.create_agent`) nhưng vẫn hoạt động đầy đủ tới bản 2.0 — dùng tạm để
tránh thêm dependency `langchain` (full package) chỉ cho 1 hàm.
"""
from __future__ import annotations

import logging
from typing import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.retrieval import nodes
from app.retrieval.llm_chat_model import ChatFPT
from app.retrieval.tools import query_catalog, query_graph_knowledge, query_vector_store
from app.schemas.playground import Citation

logger = logging.getLogger("retrieval.engine")

REACT_SYSTEM_PROMPT = (
    "Bạn là retrieval agent cho hệ thống hỏi-đáp tài liệu ngân hàng (điều khoản, quyền "
    "lợi, phí, sản phẩm/dịch vụ). Nhiệm vụ DUY NHẤT của bạn là tìm thông tin liên quan "
    "bằng các tool được cung cấp — KHÔNG tự trả lời câu hỏi bằng kiến thức riêng.\n"
    "- Luôn gọi query_vector_store trước để tìm đoạn văn bản liên quan.\n"
    "- Với câu hỏi LIỆT KÊ/TỔNG HỢP (vd 'có những loại phí nào', 'gồm những quyền lợi gì'), "
    "gọi query_catalog để xem mục lục đầy đủ của tài liệu, rồi dùng query_vector_store lấy "
    "dữ liệu cụ thể cho tới khi đủ các mục trong catalog.\n"
    "- Nếu câu hỏi có vẻ cần quan hệ giữa nhiều sản phẩm/điều khoản, thử thêm "
    "query_graph_knowledge.\n"
    "- Nếu kết quả lần đầu chưa đủ liên quan, thử gọi lại tool với câu truy vấn khác "
    "(diễn đạt lại/cụ thể hơn).\n"
    "- BẮT BUỘC gọi ít nhất 1 tool trước khi dừng. Khi đã có đủ thông tin thì dừng lại — "
    "không cần viết câu trả lời hoàn chỉnh, nội dung trả lời của bạn sẽ không được dùng."
)


class EngineState(TypedDict):
    question: str
    top_k: int
    normalized_question: str
    rewritten_question: str
    messages: list[BaseMessage]
    citations: list[Citation]


def _build_react_agent(model=None):
    """Tách riêng để test có thể tiêm model giả (fake BaseChatModel)."""
    return create_react_agent(
        model=model or ChatFPT(),
        tools=[query_vector_store, query_catalog, query_graph_knowledge],
        prompt=REACT_SYSTEM_PROMPT,
    )


def _normalize_step(state: EngineState) -> dict:
    return {"normalized_question": nodes.normalize(state["question"])}


def _rewrite_step(state: EngineState) -> dict:
    rewritten = nodes.rewrite(state["normalized_question"])
    return {"rewritten_question": rewritten, "messages": [HumanMessage(content=rewritten)]}


def _make_react_step(react_agent):
    def _react_step(state: EngineState) -> dict:
        try:
            result = react_agent.invoke(
                {"messages": state["messages"]},
                config={"recursion_limit": settings.retrieval_agent_max_steps},
            )
            messages = result["messages"]
        except GraphRecursionError:
            logger.warning(
                "[react] vượt recursion_limit=%s — dùng messages đã có (nếu có tool "
                "result nào thì rerank vẫn dùng được, không lỗi cả request)",
                settings.retrieval_agent_max_steps,
            )
            messages = state["messages"]
        return {"messages": messages}

    return _react_step


def _rerank_step(state: EngineState) -> dict:
    return {"citations": nodes.rerank(state["messages"], state["top_k"])}


def build_graph(model=None):
    """model=None -> dùng ChatFPT() thật. Truyền model giả để test offline không gọi FPT."""
    react_agent = _build_react_agent(model)

    graph = StateGraph(EngineState)
    graph.add_node("normalize", _normalize_step)
    graph.add_node("rewrite", _rewrite_step)
    graph.add_node("react", _make_react_step(react_agent))
    graph.add_node("rerank", _rerank_step)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "rewrite")
    graph.add_edge("rewrite", "react")
    graph.add_edge("react", "rerank")
    graph.add_edge("rerank", END)
    return graph.compile()


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = build_graph()
    return _engine


def retrieve(question: str, top_k: int = 5) -> dict:
    """Chạy outer graph: normalize -> rewrite -> react (vector/graph tools) -> rerank.

    Trả về cả citations lẫn trace (câu hỏi đã normalize/rewrite, danh sách tool đã gọi
    kèm số hit) — caller (MCP tool) quyết định lộ ra bao nhiêu cho từng loại client.
    """
    result = _get_engine().invoke({"question": question, "top_k": top_k, "messages": []})
    return {
        "citations": result["citations"],
        "normalized_question": result["normalized_question"],
        "rewritten_question": result["rewritten_question"],
        "tool_calls": nodes.build_trace(result["messages"]),
    }
