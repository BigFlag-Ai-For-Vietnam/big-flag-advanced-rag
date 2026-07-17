"""Router playground: RAG query dựa trên Qdrant, hỗ trợ stream (SSE) + non-stream."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.retrieval.mcp import client as retrieval_client
from app.schemas.playground import (
    Citation,
    McpRetrieveConfig,
    McpRetrieveRequest,
    McpRetrieveResponse,
    QueryRequest,
    QueryResponse,
)
from app.services import llm_client

router = APIRouter(prefix="/api/playground", tags=["playground"])
logger = logging.getLogger("playground")

SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)


def _build_messages(question: str, citations: list[Citation]) -> list[dict]:
    context_blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(context_blocks) if context_blocks else "(không có ngữ cảnh)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {question}",
        },
    ]


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")

    # Retrieval Engine chạy như service riêng — gọi đúng 1 lần qua MCP, không tự làm
    # thêm orchestration (embed/search) ở đây nữa.
    result = await retrieval_client.retrieve(req.question, req.top_k)
    citations = result.citations
    messages = _build_messages(req.question, citations)

    if req.stream:
        return StreamingResponse(_stream_answer(messages, citations), media_type="text/event-stream")

    answer = llm_client.chat(messages, temperature=0.2, max_tokens=1024, tag="qa")
    return QueryResponse(answer=answer, citations=citations)


@router.post("/mcp-retrieve", response_model=McpRetrieveResponse)
async def mcp_retrieve(req: McpRetrieveRequest):
    """Debug/test riêng Retrieval Engine qua MCP — trả citation thô, KHÔNG sinh câu trả
    lời. Dùng cho tab "MCP Playground" ở FE để quan sát ảnh hưởng của normalize/rewrite/
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
        config=config,
    )


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
