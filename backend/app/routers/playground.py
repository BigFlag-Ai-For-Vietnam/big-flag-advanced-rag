"""Router playground: RAG hỏi–đáp.

Retrieval dùng **Retrieval Engine (LangGraph)** chạy như service riêng, gọi qua MCP
(app.retrieval.mcp.client). Engine tự làm normalize -> rewrite -> ReAct (query_vector_store
+ query_catalog + query_graph_knowledge) -> rerank, trả về citations. Backend chỉ:
  1) gọi engine đúng 1 lần lấy citations,
  2) lấy CATALOG (SQLite) của các tài liệu được trích để hiển thị + đưa vào ngữ cảnh,
  3) sinh câu trả lời (stream/non-stream).

Fallback: nếu MCP không sẵn sàng/lỗi -> retrieve thẳng Qdrant (không có normalize/rewrite/
rerank) để /query không chết.

- /query        : QA chính (stream SSE + non-stream), kèm catalogs.
- /mcp-retrieve : debug riêng Retrieval Engine (citations + trace, KHÔNG sinh câu trả lời).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Document
from app.retrieval.mcp import client as retrieval_client
from app.schemas.playground import (
    CatalogInfo,
    Citation,
    McpRetrieveConfig,
    McpRetrieveRequest,
    McpRetrieveResponse,
    QueryRequest,
    QueryResponse,
    SubgoalCoverage,
)
from app.services import catalog_service, embedding_service, llm_client, qdrant_service

router = APIRouter(prefix="/api/playground", tags=["playground"])
logger = logging.getLogger("playground")

SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "CATALOG là bản đồ mục lục của tài liệu (chỉ tên mục, không có giá trị) — dùng để trả "
    "lời ĐẦY ĐỦ, đặc biệt câu hỏi liệt kê (đối chiếu catalog xem đã đủ mục chưa). "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)


# ------------------------- retrieval -------------------------

async def _retrieve(question: str, top_k: int) -> tuple[list[Citation], list[SubgoalCoverage]]:
    """Gọi Retrieval Engine (agentic planning) qua MCP → citations + coverage từng sub-goal.
    Nếu lỗi -> fallback retrieve thẳng Qdrant (không planning)."""
    try:
        result = await retrieval_client.retrieve(question, top_k)
        return result.citations, result.subgoals
    except Exception as exc:  # noqa: BLE001 — MCP down/lỗi -> fallback
        logger.warning("Retrieval Engine (MCP) lỗi, fallback Qdrant trực tiếp: %s", exc)
        return _simple_retrieve(question, top_k), []


def _simple_retrieve(question: str, top_k: int) -> list[Citation]:
    hits = qdrant_service.search(
        embedding_service.embed_query(question), top_k, active_only=settings.retrieval_exclude_inactive
    )
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


def _fetch_catalogs(db: Session, citations: list[Citation]) -> list[CatalogInfo]:
    """Lấy catalog document-level (SQLite) cho các tài liệu xuất hiện trong citations."""
    doc_ids: list[str] = []
    for c in citations:
        if c.document_id and c.document_id not in doc_ids:
            doc_ids.append(c.document_id)
    out: list[CatalogInfo] = []
    for did in doc_ids:
        doc = db.get(Document, did)
        if settings.retrieval_exclude_inactive and doc and not doc.is_active:
            continue
        if doc and doc.catalog and doc.catalog.get("tree"):
            out.append(CatalogInfo(document_id=doc.id, title=doc.title, catalog=doc.catalog))
    return out


# ------------------------- answer -------------------------

def _build_messages(
    question: str,
    citations: list[Citation],
    catalogs: list[CatalogInfo],
    subgoals: list[SubgoalCoverage],
) -> list[dict]:
    blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(blocks) if blocks else "(không có ngữ cảnh)"
    catalog_text = "\n\n".join(
        catalog_service.format_catalog_text(c.title, c.catalog) for c in catalogs
    ).strip()
    # Các sub-goal chưa đủ bằng chứng -> yêu cầu LLM nêu rõ phần còn thiếu thay vì bịa.
    missing = [f"- {s.description}: {s.note or 'chưa đủ bằng chứng'}" for s in subgoals if not s.satisfied]

    parts = [f"NGỮ CẢNH:\n{context}"]
    if catalog_text:
        parts.append(f"CATALOG:\n{catalog_text}")
    if missing:
        parts.append("PHẦN CÒN THIẾU BẰNG CHỨNG (nêu rõ trong câu trả lời, KHÔNG bịa):\n" + "\n".join(missing))
    parts.append(f"CÂU HỎI: {question}")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ------------------------- endpoints -------------------------

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, db: Session = Depends(get_db)):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")

    if req.stream:
        return StreamingResponse(_stream_query(db, req), media_type="text/event-stream")

    citations, coverage = await _retrieve(req.question, req.top_k)
    catalogs = _fetch_catalogs(db, citations)
    answer = llm_client.chat(
        _build_messages(req.question, citations, catalogs, coverage),
        temperature=0.2, max_tokens=1024, tag="qa",
    )
    return QueryResponse(answer=answer, citations=citations, catalogs=catalogs)


async def _stream_query(db: Session, req: QueryRequest):
    """SSE: gửi catalogs + citations trước, rồi stream token, kết thúc [DONE]."""
    try:
        citations, coverage = await _retrieve(req.question, req.top_k)
        catalogs = _fetch_catalogs(db, citations)
        yield _sse({"type": "catalogs", "catalogs": [c.model_dump() for c in catalogs]})
        yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})
        yield _sse({"type": "coverage", "subgoals": [s.model_dump() for s in coverage]})
        for delta in llm_client.chat_stream(
            _build_messages(req.question, citations, catalogs, coverage),
            temperature=0.2, max_tokens=1024, tag="qa_stream",
        ):
            yield _sse({"type": "token", "content": delta})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream lỗi")
        yield _sse({"type": "error", "message": str(exc)})
    yield "data: [DONE]\n\n"


@router.post("/mcp-retrieve", response_model=McpRetrieveResponse)
async def mcp_retrieve(req: McpRetrieveRequest):
    """Debug/test riêng Retrieval Engine qua MCP — trả citation thô + trace, KHÔNG sinh câu
    trả lời. Dùng cho tab "MCP Playground" ở FE để quan sát ảnh hưởng của normalize/rewrite/
    rerank (đổi RETRIEVAL_ENABLE_* trong .env rồi gọi lại là thấy khác biệt)."""
    result = await retrieval_client.retrieve(req.question, req.top_k)
    config = McpRetrieveConfig(
        normalize=settings.retrieval_enable_normalize,
        rewrite=settings.retrieval_enable_rewrite,
        rerank=settings.retrieval_enable_rerank,
        agent_max_steps=settings.retrieval_agent_max_steps,
    )
    return McpRetrieveResponse(
        citations=result.citations,
        normalized_question=result.normalized_question,
        rewritten_question=result.rewritten_question,
        tool_calls=result.tool_calls,
        subgoals=result.subgoals,
        config=config,
    )
