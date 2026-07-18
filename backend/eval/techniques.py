"""Registry kỹ thuật RAG cho eval (FR-17, rev 3): mọi biến thể RAG (trivial hiện tại; agentic,
agentic-kg-vector sau này) đứng sau MỘT interface `(question, top_k) -> (response,
retrieved_contexts)` để `judge`/runner không cần biết chi tiết implementation — thêm biến thể
mới chỉ là thêm 1 entry vào `TECHNIQUES`, không đổi dataset/judge.

Import nhẹ — module này KHÔNG được kéo ragas/mlflow (NFR-1/2); `qa_service` là dep backend
bình thường nên import thẳng là an toàn.
"""
from __future__ import annotations

from typing import Callable

from app.services import qa_service

TechniqueFn = Callable[[str, int], tuple[str, list[str]]]


def _trivial(question: str, top_k: int) -> tuple[str, list[str]]:
    """Kỹ thuật RAG baseline: retrieval dense thẳng Qdrant + answer (`qa_service.answer`).
    KHÔNG phải flow playground hiện tại (playground đã lên agentic engine) — đây là baseline
    RAG-only để so sánh."""
    response, citations = qa_service.answer(question, top_k)
    return response, [c.final_content for c in citations]


# --- Agentic technique: ĐÚNG flow playground hiện tại (LangGraph Retrieval Engine qua MCP) ---
# Prompt/answer sao chép nguyên văn từ routers/playground.py để eval == prod. Import mcp/engine
# LAZY trong hàm (module này phải import nhẹ, không kéo mcp khi chỉ dùng 'trivial').

_SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "CATALOG là bản đồ mục lục của tài liệu (chỉ tên mục, không có giá trị) — dùng để trả "
    "lời ĐẦY ĐỦ, đặc biệt câu hỏi liệt kê (đối chiếu catalog xem đã đủ mục chưa). "
    "TRI THỨC ĐỒ THỊ (nếu có) là quan hệ giữa văn bản/khái niệm (căn cứ/thay thế/tham chiếu/"
    "ưu tiên hơn, hoặc nhiều giá trị khác nhau cho cùng 1 khái niệm) — dùng để SUY LUẬN quan "
    "hệ/xung đột/thay thế xuyên văn bản, KHÔNG phải trích dẫn nguyên văn; trích dẫn [số] vẫn "
    "chỉ trỏ vào NGỮ CẢNH (đoạn văn bản), không trỏ vào tri thức đồ thị. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)


def _format_graph_facts(graph_facts) -> str:
    lines = []
    for f in graph_facts:
        prop_txt = f" ({f.properties})" if f.properties else ""
        source_txt = f" [nguồn: {f.source_document_title}]" if f.source_document_title else ""
        lines.append(f"- {f.source_entity} --{f.relation}--> {f.target_entity}{prop_txt}{source_txt}")
    return "\n".join(lines)


def _build_messages(question, citations, subgoals, graph_facts) -> list[dict]:
    """Sao chép routers/playground.py::_build_messages, bỏ block CATALOG (eval không nối SQLite)."""
    blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(blocks) if blocks else "(không có ngữ cảnh)"
    graph_text = _format_graph_facts(graph_facts)
    missing = [f"- {s.description}: {s.note or 'chưa đủ bằng chứng'}" for s in subgoals if not s.satisfied]
    parts = [f"NGỮ CẢNH:\n{context}"]
    if graph_text:
        parts.append(
            "TRI THỨC ĐỒ THỊ (quan hệ giữa văn bản/khái niệm — KHÔNG phải trích dẫn nguyên văn):\n"
            + graph_text
        )
    if missing:
        parts.append("PHẦN CÒN THIẾU BẰNG CHỨNG (nêu rõ trong câu trả lời, KHÔNG bịa):\n" + "\n".join(missing))
    parts.append(f"CÂU HỎI: {question}")
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


import threading as _threading

_loop = None
_connected = False
_conn_lock = _threading.Lock()


def _agentic(question: str, top_k: int) -> tuple[str, list[str]]:
    """Kỹ thuật RAG = Retrieval Engine agentic (LangGraph) qua MCP — ĐÚNG flow playground:
    retrieve() (normalize→rewrite→plan→gather→assess→loop) trả citations + graph_facts, rồi tự
    sinh câu trả lời bằng cùng SYSTEM_PROMPT/_build_messages như playground. Yêu cầu retrieval-mcp
    service đang chạy tại settings.retrieval_mcp_url (mặc định http://localhost:8100/mcp)."""
    import asyncio

    from app.retrieval.mcp import client as retrieval_client
    from app.services import llm_client

    global _loop, _connected
    citations, subgoals, graph_facts = None, [], []
    with _conn_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
        # 2 lần thử retrieve, mỗi lần có TIMEOUT (agentic engine đôi khi treo phiên MCP -> nếu
        # không timeout sẽ treo cả run). Timeout/lỗi -> reconnect rồi thử lại.
        for attempt in range(2):
            try:
                if not _connected:
                    _loop.run_until_complete(retrieval_client.connect())
                    _connected = True
                result = _loop.run_until_complete(
                    asyncio.wait_for(retrieval_client.retrieve(question, top_k), timeout=120)
                )
                citations, subgoals, graph_facts = result.citations, result.subgoals, result.graph_facts
                break
            except Exception:  # timeout / phiên rớt -> ép reconnect cho lần sau
                _connected = False
                try:
                    _loop.run_until_complete(retrieval_client.connect())
                    _connected = True
                except Exception:
                    pass

    if citations is None:
        # Fallback = retrieve dense thẳng Qdrant (giống playground khi MCP hỏng) — bảo đảm mẫu
        # vẫn hoàn tất thay vì treo/hỏng cả run; sample này mất phần agentic/graph.
        from app.config import settings
        from app.services import embedding_service, qdrant_service

        hits = qdrant_service.search(
            embedding_service.embed_query(question), top_k,
            active_only=settings.retrieval_exclude_inactive,
        )
        citations = [
            type("C", (), {
                "title": h["payload"].get("title", ""),
                "chunk_index": h["payload"].get("chunk_index", -1),
                "final_content": h["payload"].get("final_content", ""),
            })() for h in hits
        ]
        subgoals, graph_facts = [], []

    msgs = _build_messages(question, citations, subgoals, graph_facts)
    # 4096 (không phải 1024 như default playground): câu trả lời tuân thủ hay liệt kê/so sánh nhiều
    # điều khoản xuyên văn bản nên cần dài, tránh bị cắt cụt làm hỏng điểm chấm.
    answer = llm_client.chat(msgs, temperature=0.2, max_tokens=4096, tag="qa")
    return answer, [c.final_content for c in citations]


TECHNIQUES: dict[str, TechniqueFn] = {
    "trivial": _trivial,
    "agentic": _agentic,
}


def resolve(name: str) -> TechniqueFn:
    """Tra registry theo tên; tên không tồn tại -> ValueError liệt kê tên đã đăng ký."""
    try:
        return TECHNIQUES[name]
    except KeyError:
        registered = ", ".join(sorted(TECHNIQUES))
        raise ValueError(
            f"Kỹ thuật RAG không xác định: '{name}'. Đã đăng ký: {registered}"
        ) from None
