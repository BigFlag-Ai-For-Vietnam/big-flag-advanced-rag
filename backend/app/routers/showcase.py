"""Showcase: chạy Advanced RAG và Raw Vector RAG trên cùng một câu hỏi.

Endpoint trả SSE multiplexed. Mỗi event có ``pipeline`` để frontend cập nhật hai card độc
lập; lỗi ở một pipeline không hủy pipeline còn lại. Advanced không fallback âm thầm sang
raw retrieval vì điều đó làm sai ý nghĩa của phép so sánh.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.db import SessionLocal
from app.retrieval.mcp import client as retrieval_client
from app.schemas.playground import ShowcaseCompareRequest
from app.services import llm_client, qa_service

router = APIRouter(prefix="/api/showcase", tags=["showcase"])
logger = logging.getLogger("showcase")


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _safe_pipeline_error(stage: str) -> str:
    if stage == "generate":
        return "Dịch vụ AI tạm thời gián đoạn khi soạn câu trả lời. Vui lòng thử lại."
    return "Dịch vụ AI tạm thời gián đoạn khi truy hồi. Vui lòng thử lại."


async def _emit(queue: asyncio.Queue, payload: dict[str, Any], *, terminal: bool = False) -> None:
    await queue.put((payload, terminal))


async def _run_raw(
    req: ShowcaseCompareRequest, queue: asyncio.Queue, started: float, run_id: str = ""
) -> None:
    pipeline = "raw"
    sequence = 0
    current_stage = "kb_search"

    async def progress(stage: str, status: str, label: str, **extra: Any) -> None:
        nonlocal sequence
        sequence += 1
        await _emit(queue, {
            "type": "progress", "run_id": run_id, "pipeline": pipeline, "seq": sequence,
            "stage": stage, "status": status, "label": label,
            "elapsed_ms": _elapsed_ms(started), **extra,
        })

    try:
        retrieval_started = time.perf_counter()
        await progress("kb_search", "started", "Đang embed câu hỏi và tìm Qdrant")
        citations = await asyncio.to_thread(qa_service.retrieve, req.question, req.top_k)
        retrieval_ms = _elapsed_ms(started)
        await progress(
            "kb_search", "completed", f"Dense retrieval tìm thấy {len(citations)} đoạn",
            duration_ms=_elapsed_ms(retrieval_started), detail={"hit_count": len(citations)},
        )
        await _emit(
            queue,
            {
                "type": "pipeline_context",
                "pipeline": pipeline,
                "retrieval_ms": retrieval_ms,
                "citations": [c.model_dump() for c in citations],
                "trace": [
                    {"stage": "embedding", "label": "Embed câu hỏi gốc"},
                    {
                        "stage": "qdrant",
                        "label": f"Dense vector top-{req.top_k}",
                        "hit_count": len(citations),
                    },
                ],
            },
        )

        first_token_ms: int | None = None
        generation_started = time.perf_counter()
        current_stage = "generate"
        await progress("generate", "started", "Đang soạn câu trả lời")
        async for delta in llm_client.chat_stream_async(
            qa_service.build_messages(req.question, citations),
            temperature=0.2,
            max_tokens=1024,
            tag="showcase_raw",
        ):
            if first_token_ms is None:
                first_token_ms = _elapsed_ms(started)
            await _emit(
                queue,
                {"type": "pipeline_token", "pipeline": pipeline, "content": delta},
            )
        await progress(
            "generate", "completed", "Đã soạn xong câu trả lời",
            duration_ms=_elapsed_ms(generation_started),
        )
        await _emit(
            queue,
            {
                "type": "pipeline_done",
                "pipeline": pipeline,
                "retrieval_ms": retrieval_ms,
                "first_token_ms": first_token_ms,
                "total_ms": _elapsed_ms(started),
                "citation_count": len(citations),
            },
            terminal=True,
        )
        logger.info(
            "Showcase raw done: retrieval_ms=%s total_ms=%s citations=%s",
            retrieval_ms,
            _elapsed_ms(started),
            len(citations),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — pipeline kia vẫn phải chạy
        logger.exception("Raw showcase pipeline lỗi")
        await progress(
            current_stage, "failed", f"Lỗi tại bước {'soạn câu trả lời' if current_stage == 'generate' else 'dense retrieval'}",
            detail={"reason": type(exc).__name__},
        )
        await _emit(
            queue,
            {
                "type": "pipeline_error",
                "pipeline": pipeline,
                "message": _safe_pipeline_error(current_stage),
                "total_ms": _elapsed_ms(started),
            },
            terminal=True,
        )


async def _run_advanced(
    req: ShowcaseCompareRequest, queue: asyncio.Queue, started: float, run_id: str = ""
) -> None:
    pipeline = "advanced"
    sequence = 0
    current_stage = "normalize"
    current_detail: dict[str, Any] = {}

    async def progress(event: dict) -> None:
        nonlocal sequence, current_stage, current_detail
        sequence += 1
        next_stage = event.get("stage", current_stage)
        if next_stage != current_stage:
            current_detail = {}
        current_stage = next_stage
        current_detail = event.get("detail") or current_detail
        await _emit(queue, {
            "type": "progress", "run_id": run_id, "pipeline": pipeline, "seq": sequence,
            "stage": event.get("stage", "finalize"),
            "status": event.get("status", "completed"),
            "label": event.get("label", "Đang xử lý"),
            "elapsed_ms": _elapsed_ms(started),
            **({"duration_ms": event["duration_ms"]} if event.get("duration_ms") is not None else {}),
            **({"detail": event["detail"]} if event.get("detail") else {}),
        })

    try:
        result = await retrieval_client.retrieve(req.question, req.top_k, progress=progress)
        with SessionLocal() as db:
            catalogs = qa_service.fetch_catalogs(db, result.citations)
        retrieval_ms = _elapsed_ms(started)
        await _emit(
            queue,
            {
                "type": "pipeline_context",
                "pipeline": pipeline,
                "retrieval_ms": retrieval_ms,
                "citations": [c.model_dump() for c in result.citations],
                "graph_facts": [fact.model_dump() for fact in result.graph_facts],
                "catalogs": [c.model_dump() for c in catalogs],
                "normalized_question": result.normalized_question,
                "rewritten_question": result.rewritten_question,
                "tool_calls": [t.model_dump() for t in result.tool_calls],
                "subgoals": [s.model_dump() for s in result.subgoals],
            },
        )

        first_token_ms: int | None = None
        generation_started = time.perf_counter()
        await progress({"stage": "generate", "status": "started", "label": "Đang soạn câu trả lời"})
        async for delta in llm_client.chat_stream_async(
            qa_service.build_advanced_messages(
                req.question,
                result.citations,
                catalogs,
                result.subgoals,
                result.graph_facts,
            ),
            temperature=0.2,
            max_tokens=1024,
            tag="showcase_advanced",
        ):
            if first_token_ms is None:
                first_token_ms = _elapsed_ms(started)
            await _emit(
                queue,
                {"type": "pipeline_token", "pipeline": pipeline, "content": delta},
            )
        await progress({
            "stage": "generate", "status": "completed", "label": "Đã soạn xong câu trả lời",
            "duration_ms": _elapsed_ms(generation_started),
        })
        await _emit(
            queue,
            {
                "type": "pipeline_done",
                "pipeline": pipeline,
                "retrieval_ms": retrieval_ms,
                "first_token_ms": first_token_ms,
                "total_ms": _elapsed_ms(started),
                "citation_count": len(result.citations),
                "graph_fact_count": len(result.graph_facts),
            },
            terminal=True,
        )
        logger.info(
            "Showcase advanced done: retrieval_ms=%s total_ms=%s citations=%s",
            retrieval_ms,
            _elapsed_ms(started),
            len(result.citations),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — pipeline kia vẫn phải chạy
        logger.exception("Advanced showcase pipeline lỗi")
        await progress({
            "stage": current_stage,
            "status": "failed",
            "label": f"Lỗi tại bước {current_stage}",
            "detail": {**current_detail, "reason": type(exc).__name__},
        })
        await _emit(
            queue,
            {
                "type": "pipeline_error",
                "pipeline": pipeline,
                "message": _safe_pipeline_error(current_stage),
                "total_ms": _elapsed_ms(started),
            },
            terminal=True,
        )


async def _compare_stream(req: ShowcaseCompareRequest, request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    started = time.perf_counter()
    run_id = str(uuid.uuid4())
    workers = [
        asyncio.create_task(_run_advanced(req, queue, started, run_id)),
        asyncio.create_task(_run_raw(req, queue, started, run_id)),
    ]
    remaining = len(workers)
    last_emit = time.perf_counter()
    try:
        yield _sse(
            {
                "type": "run_started",
                "run_id": run_id,
                "question": req.question,
                "top_k": req.top_k,
                "pipelines": ["advanced", "raw"],
            }
        )
        while remaining:
            if await request.is_disconnected():
                break
            try:
                payload, terminal = await asyncio.wait_for(queue.get(), timeout=1.0)
            except TimeoutError:
                if time.perf_counter() - last_emit >= 15:
                    yield ": ping\n\n"
                    last_emit = time.perf_counter()
                continue
            yield _sse(payload)
            last_emit = time.perf_counter()
            if terminal:
                remaining -= 1
        if remaining == 0:
            yield _sse({"type": "run_done", "total_ms": _elapsed_ms(started)})
            yield "data: [DONE]\n\n"
    finally:
        for worker in workers:
            if not worker.done():
                worker.cancel()
        for worker in workers:
            with suppress(asyncio.CancelledError):
                await worker


@router.post("/compare")
async def compare(req: ShowcaseCompareRequest, request: Request):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")
    return StreamingResponse(
        _compare_stream(req, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
