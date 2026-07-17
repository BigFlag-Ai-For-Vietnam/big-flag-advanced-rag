"""Router playground: RAG query dựa trên Qdrant, hỗ trợ stream (SSE) + non-stream."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.playground import Citation, QueryRequest, QueryResponse
from app.services import llm_client, qa_service

router = APIRouter(prefix="/api/playground", tags=["playground"])
logger = logging.getLogger("playground")


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")

    citations = qa_service.retrieve(req.question, req.top_k)
    messages = qa_service.build_messages(req.question, citations)

    if req.stream:
        return StreamingResponse(_stream_answer(messages, citations), media_type="text/event-stream")

    answer_text = llm_client.chat(messages, temperature=0.2, max_tokens=1024, tag="qa")
    return QueryResponse(answer=answer_text, citations=citations)


def _stream_answer(messages: list[dict], citations: list[Citation]):
    """SSE: gửi citations trước, rồi stream token, kết thúc bằng [DONE]."""
    payload = {"type": "citations", "citations": [c.model_dump() for c in citations]}
    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    try:
        for delta in llm_client.chat_stream(messages, temperature=0.2, max_tokens=1024, tag="qa_stream"):
            yield f"data: {json.dumps({'type': 'token', 'content': delta}, ensure_ascii=False)}\n\n"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream lỗi")
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
