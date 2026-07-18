"""Router playground: RAG hỏi–đáp.

- Mặc định dùng ReAct agent (catalog-aware): catalog cho agent biết tổng thể tài liệu,
  chunk-based cung cấp dữ liệu cụ thể, agent tự đánh giá đủ chưa (đặc biệt câu liệt kê).
- Fallback: nếu agent không dựng được (thiếu package) hoặc lỗi -> one-shot QA đơn giản.
- Hỗ trợ cả stream (SSE) và non-stream.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.schemas.playground import CatalogInfo, Citation, QueryRequest, QueryResponse
from app.services import agent_service, embedding_service, llm_client, qdrant_service

router = APIRouter(prefix="/api/playground", tags=["playground"])
logger = logging.getLogger("playground")

SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)


# ------------------------- One-shot QA (fallback) -------------------------

def _simple_retrieve(question: str, top_k: int) -> list[Citation]:
    hits = qdrant_service.search(embedding_service.embed_query(question), top_k)
    return [
        Citation(
            document_id=h["payload"].get("document_id", ""),
            title=h["payload"].get("title", ""),
            chunk_index=h["payload"].get("chunk_index", -1),
            score=h["score"],
            final_content=h["payload"].get("final_content", ""),
        )
        for h in hits
    ]


def _simple_messages(question: str, citations: list[Citation]) -> list[dict]:
    blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(blocks) if blocks else "(không có ngữ cảnh)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {question}"},
    ]


# ------------------------- helpers -------------------------

def _to_citations(raw: list[dict]) -> list[Citation]:
    return [Citation(**c) for c in raw]


def _to_catalogs(raw: list[dict]) -> list[CatalogInfo]:
    return [
        CatalogInfo(document_id=c["document_id"], title=c["title"], catalog=c["catalog"])
        for c in raw
    ]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ------------------------- endpoint -------------------------

@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")

    if req.stream:
        return StreamingResponse(
            _stream_query(db, req), media_type="text/event-stream"
        )

    # -------- non-stream --------
    if req.use_agent:
        try:
            answer, citations_raw, catalogs_raw = agent_service.answer(db, req.question, req.top_k)
            return QueryResponse(
                answer=answer,
                citations=_to_citations(citations_raw),
                catalogs=_to_catalogs(catalogs_raw),
            )
        except Exception as exc:  # noqa: BLE001 — fallback one-shot
            logger.warning("Agent lỗi, fallback one-shot QA: %s", exc)

    citations = _simple_retrieve(req.question, req.top_k)
    answer = llm_client.chat(_simple_messages(req.question, citations), temperature=0.2, max_tokens=1024, tag="qa")
    return QueryResponse(answer=answer, citations=citations, catalogs=[])


def _stream_query(db: Session, req: QueryRequest):
    """SSE: gửi catalogs + citations trước, rồi stream token, kết thúc [DONE]."""
    # Thử agent trước; nếu dựng lỗi -> fallback.
    if req.use_agent:
        try:
            token_gen, citations_raw, catalogs_raw = agent_service.stream(db, req.question, req.top_k)
            yield _sse({"type": "catalogs", "catalogs": [c.model_dump() for c in _to_catalogs(catalogs_raw)]})
            yield _sse({"type": "citations", "citations": [c.model_dump() for c in _to_citations(citations_raw)]})
            try:
                for token in token_gen():
                    yield _sse({"type": "token", "content": token})
                # citations có thể được bồi thêm khi agent gọi tool -> gửi bản cập nhật cuối.
                yield _sse({"type": "citations", "citations": [c.model_dump() for c in _to_citations(citations_raw)]})
            except Exception as exc:  # noqa: BLE001 — lỗi giữa stream
                logger.exception("Agent stream lỗi giữa chừng")
                yield _sse({"type": "error", "message": str(exc)})
            yield "data: [DONE]\n\n"
            return
        except Exception as exc:  # noqa: BLE001 — dựng agent lỗi -> fallback
            logger.warning("Agent stream không dựng được, fallback one-shot: %s", exc)

    # -------- fallback one-shot stream --------
    citations = _simple_retrieve(req.question, req.top_k)
    yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})
    try:
        for delta in llm_client.chat_stream(
            _simple_messages(req.question, citations), temperature=0.2, max_tokens=1024, tag="qa_stream"
        ):
            yield _sse({"type": "token", "content": delta})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream lỗi")
        yield _sse({"type": "error", "message": str(exc)})
    yield "data: [DONE]\n\n"
