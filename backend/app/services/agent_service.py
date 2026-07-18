"""ReAct agent cho Playground (LlamaIndex ReActAgent).

Luồng:
1. Retrieve sơ bộ theo câu hỏi -> xác định các document liên quan -> lấy CATALOG của chúng.
2. Nhét catalog (bản đồ mục lục, không có data) vào context của agent -> agent biết tổng
   thể tài liệu có những mục gì / bao nhiêu mục.
3. Agent dùng tool `retrieve` (chunk-based) để lấy DATA cụ thể, tự đánh giá đã đủ chưa
   (đặc biệt câu hỏi liệt kê), lặp reason->act->observe rồi trả lời có trích dẫn.

Ghi chú:
- LlamaIndex ReActAgent chạy ReAct dạng TEXT (Thought/Action/Observation) nên KHÔNG cần
  model hỗ trợ native function-calling -> chạy được với GLM trên FPT.
- Import LlamaIndex/OpenAILike theo kiểu lazy: nếu thiếu package hoặc agent lỗi, caller
  fallback sang one-shot QA (xem playground router).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document
from app.services import embedding_service, qdrant_service

logger = logging.getLogger("agent_service")

AGENT_MAX_ITERATIONS = 8

SYSTEM_CONTEXT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu nội bộ (thẻ, bảo hiểm, quy trình...). "
    "Luôn trả lời bằng tiếng Việt và CHỈ dựa trên dữ liệu lấy được từ công cụ.\n"
    "Bạn có công cụ `retrieve` để lấy các đoạn nội dung (chunk) chứa dữ liệu cụ thể.\n"
    "Dưới đây là CATALOG — bản đồ mục lục theo facet của các tài liệu liên quan. Catalog "
    "chỉ liệt kê TÊN các mục (không có giá trị). Hãy dùng catalog để biết tổng thể tài liệu "
    "có những mục nào và cần lấy ĐỦ bao nhiêu mục — đặc biệt với câu hỏi liệt kê "
    "(vd 'có những loại phí nào'): đối chiếu catalog, gọi `retrieve` nhiều lần cho tới khi "
    "đủ mục, rồi mới trả lời.\n"
    "Nếu dữ liệu không đủ, nói rõ là không tìm thấy trong tài liệu. Trích nguồn khi phù hợp."
)


class AgentUnavailable(RuntimeError):
    """Không dựng được agent (thiếu package hoặc chưa cấu hình)."""


def _hit_to_citation(hit: dict) -> dict:
    p = hit.get("payload", {})
    return {
        "document_id": p.get("document_id", ""),
        "title": p.get("title", ""),
        "chunk_index": p.get("chunk_index", -1),
        "score": float(hit.get("score", 0.0)),
        "final_content": p.get("final_content", ""),
    }


def _add_citations(collector: list[dict], hits: list[dict]) -> None:
    """Thêm citations vào collector, dedup theo (document_id, chunk_index)."""
    seen = {(c["document_id"], c["chunk_index"]) for c in collector}
    for h in hits:
        c = _hit_to_citation(h)
        key = (c["document_id"], c["chunk_index"])
        if key not in seen:
            collector.append(c)
            seen.add(key)


def _collect_catalogs(db: Session, hits: list[dict]) -> list[dict]:
    """Lấy catalog document-level cho các document xuất hiện trong hits (dedup theo doc)."""
    from app.services.catalog_service import format_catalog_text

    doc_ids: list[str] = []
    for h in hits:
        did = h.get("payload", {}).get("document_id")
        if did and did not in doc_ids:
            doc_ids.append(did)

    catalogs: list[dict] = []
    for did in doc_ids:
        doc = db.get(Document, did)
        if doc and doc.catalog and doc.catalog.get("tree"):
            catalogs.append(
                {
                    "document_id": doc.id,
                    "title": doc.title,
                    "catalog": doc.catalog,
                    "text": format_catalog_text(doc.title, doc.catalog),
                }
            )
    return catalogs


def _build_llm():
    """Dựng LLM adapter cho LlamaIndex trỏ tới FPT (OpenAI-compatible)."""
    from llama_index.llms.openai_like import OpenAILike

    if not settings.fpt_chat_model or not settings.fpt_api_key:
        raise AgentUnavailable("Chưa cấu hình FPT_CHAT_MODEL / FPT_API_KEY.")

    additional_kwargs: dict = {}
    if settings.fpt_disable_thinking:
        # tắt reasoning của GLM để output ổn định + đúng format ReAct
        additional_kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}

    return OpenAILike(
        model=settings.fpt_chat_model,
        api_base=settings.fpt_base_url,
        api_key=settings.fpt_api_key,
        is_chat_model=True,
        is_function_calling_model=False,  # ép ReActAgent dùng ReAct dạng text
        temperature=0.2,
        max_tokens=4096,
        context_window=32000,
        timeout=settings.llm_timeout,
        additional_kwargs=additional_kwargs,
    )


def _prepare(db: Session, question: str, top_k: int):
    """Dựng agent + seed citations/catalogs từ retrieval sơ bộ. Raise AgentUnavailable nếu không dựng được."""
    try:
        from llama_index.core.agent import ReActAgent
        from llama_index.core.tools import FunctionTool
    except ImportError as exc:  # package agent chưa cài
        raise AgentUnavailable(f"Thiếu package LlamaIndex agent: {exc}") from exc

    llm = _build_llm()

    citations: list[dict] = []
    catalogs: list[dict] = []

    # Retrieval sơ bộ để xác định document + catalog liên quan (và seed citations).
    seed_hits = qdrant_service.search(embedding_service.embed_query(question), top_k)
    _add_citations(citations, seed_hits)
    catalogs.extend(_collect_catalogs(db, seed_hits))

    def retrieve(query: str) -> str:
        """Lấy các đoạn nội dung liên quan tới `query` (chunk-based). Dùng để lấy dữ liệu cụ thể."""
        hits = qdrant_service.search(embedding_service.embed_query(query), top_k)
        _add_citations(citations, hits)
        if not hits:
            return "Không tìm thấy đoạn nào phù hợp."
        blocks = []
        for h in hits:
            p = h.get("payload", {})
            blocks.append(
                f"(Tài liệu: {p.get('title', '')}, đoạn #{p.get('chunk_index', -1)})\n"
                f"{p.get('final_content', '')}"
            )
        return "\n\n---\n\n".join(blocks)

    retrieve_tool = FunctionTool.from_defaults(
        fn=retrieve,
        name="retrieve",
        description=(
            "Tìm và trả về các đoạn nội dung tài liệu liên quan tới một truy vấn tiếng Việt. "
            "Dùng để lấy dữ liệu cụ thể (số tiền, điều kiện, chi tiết mục). Có thể gọi nhiều lần "
            "với các truy vấn khác nhau để gom đủ thông tin cho câu hỏi liệt kê/so sánh."
        ),
    )

    catalog_text = "\n\n".join(c["text"] for c in catalogs if c["text"])
    context = SYSTEM_CONTEXT
    if catalog_text:
        context = f"{SYSTEM_CONTEXT}\n\n=== CATALOG CÁC TÀI LIỆU LIÊN QUAN ===\n{catalog_text}"

    agent = ReActAgent.from_tools(
        tools=[retrieve_tool],
        llm=llm,
        verbose=False,
        max_iterations=AGENT_MAX_ITERATIONS,
        context=context,
    )
    return agent, citations, catalogs


def answer(db: Session, question: str, top_k: int) -> tuple[str, list[dict], list[dict]]:
    """Non-stream: trả về (answer, citations, catalogs)."""
    agent, citations, catalogs = _prepare(db, question, top_k)
    resp = agent.chat(question)
    return str(resp).strip(), citations, catalogs


def stream(db: Session, question: str, top_k: int):
    """Stream: trả về (token_generator, citations, catalogs).

    citations được seed từ retrieval sơ bộ (gửi trước), và tiếp tục được bồi thêm khi agent
    gọi tool trong lúc chạy generator.
    """
    agent, citations, catalogs = _prepare(db, question, top_k)

    def token_gen():
        resp = agent.stream_chat(question)
        for token in resp.response_gen:
            yield token

    return token_gen, citations, catalogs
