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
- /mcp-retrieve : debug Retrieval Engine; bản stream tiếp tục sinh câu trả lời từ evidence.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.retrieval.mcp import client as retrieval_client
from app.schemas.playground import (
    CatalogInfo,
    Citation,
    GraphFact,
    McpRetrieveConfig,
    McpRetrieveRequest,
    McpRetrieveResponse,
    QueryRequest,
    QueryResponse,
    SubgoalCoverage,
)
from app.services import embedding_service, llm_client, qa_service, qdrant_service, tracing

router = APIRouter(prefix="/api/playground", tags=["playground"])
logger = logging.getLogger("playground")
ProgressCallback = Callable[[dict], Awaitable[None]]
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# ------------------------- retrieval -------------------------

async def _retrieve(
    question: str, top_k: int, *, progress: ProgressCallback | None = None
) -> tuple[list[Citation], list[GraphFact], list[SubgoalCoverage]]:
    """Gọi Retrieval Engine (agentic planning) qua MCP → citations + graph_facts + coverage
    từng sub-goal. Nếu lỗi -> fallback retrieve thẳng Qdrant (không planning, không graph)."""
    with tracing.span(
        "retrieve",
        span_type=tracing.RETRIEVER,
        inputs={"question": question, "top_k": top_k},
    ) as span:
        try:
            result = await retrieval_client.retrieve(question, top_k, progress=progress)
            citations, graph_facts, subgoals = result.citations, result.graph_facts, result.subgoals
            fallback = False
        except Exception as exc:  # noqa: BLE001 — MCP down/lỗi -> fallback
            logger.warning("Retrieval Engine (MCP) lỗi, fallback Qdrant trực tiếp: %s", exc)
            if progress:
                await progress({
                    "stage": "kb_search", "status": "warning",
                    "label": "MCP không khả dụng, chuyển sang dense retrieval",
                    "detail": {"reason": type(exc).__name__},
                })
                await progress({"stage": "kb_search", "status": "started", "label": "Đang tìm trực tiếp trong Qdrant"})
            citations = await asyncio.to_thread(_simple_retrieve, question, top_k)
            graph_facts, subgoals, fallback = [], [], True
            if progress:
                await progress({
                    "stage": "kb_search", "status": "completed",
                    "label": f"Dense retrieval tìm thấy {len(citations)} đoạn",
                    "detail": {"hit_count": len(citations)},
                })
        tracing.set_outputs(
            span,
            {
                "num_citations": len(citations),
                "num_graph_facts": len(graph_facts),
                "num_subgoals": len(subgoals),
                "fallback": fallback,
            },
        )
        return citations, graph_facts, subgoals


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
    return qa_service.fetch_catalogs(db, citations)


# ------------------------- answer -------------------------

def _build_messages(
    question: str,
    citations: list[Citation],
    catalogs: list[CatalogInfo],
    subgoals: list[SubgoalCoverage],
    graph_facts: list[GraphFact],
) -> list[dict]:
    return qa_service.build_advanced_messages(
        question, citations, catalogs, subgoals, graph_facts
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _progress_event(
    event: dict, *, run_id: str, pipeline: str, seq: int, started: float
) -> dict:
    return {
        "type": "progress",
        "run_id": run_id,
        "pipeline": pipeline,
        "seq": seq,
        "stage": event.get("stage", "finalize"),
        "status": event.get("status", "completed"),
        "label": event.get("label", "Đang xử lý"),
        "elapsed_ms": max(0, round((time.perf_counter() - started) * 1000)),
        **({"duration_ms": event["duration_ms"]} if event.get("duration_ms") is not None else {}),
        **({"detail": event["detail"]} if event.get("detail") else {}),
    }


def _safe_error_message(stage: str) -> str:
    if stage == "generate":
        return "Dịch vụ AI tạm thời gián đoạn khi soạn câu trả lời. Vui lòng thử lại."
    return "Retrieval Engine tạm thời không khả dụng. Vui lòng thử lại."


# ------------------------- endpoints -------------------------

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.fpt_chat_model or not settings.fpt_embed_model:
        raise HTTPException(status_code=503, detail="Chưa cấu hình FPT_CHAT_MODEL / FPT_EMBED_MODEL.")

    if req.stream:
        return StreamingResponse(
            _stream_query(db, req, request), media_type="text/event-stream", headers=SSE_HEADERS
        )

    with tracing.span(
        "playground_query",
        span_type=tracing.CHAIN,
        inputs={"question": req.question},
        attributes={"top_k": req.top_k, "stream": False},
    ) as root:
        citations, graph_facts, coverage = await _retrieve(req.question, req.top_k)
        catalogs = _fetch_catalogs(db, citations)
        with tracing.span("generate_answer", span_type=tracing.LLM) as gen:
            answer = llm_client.chat(
                _build_messages(req.question, citations, catalogs, coverage, graph_facts),
                temperature=0.2, max_tokens=20000, tag="qa",
            )
            tracing.set_outputs(gen, {"answer_chars": len(answer)})
        tracing.set_outputs(
            root,
            {"answer_chars": len(answer), "num_citations": len(citations), "num_graph_facts": len(graph_facts)},
        )
        return QueryResponse(answer=answer, citations=citations, catalogs=catalogs, graph_facts=graph_facts)


async def _stream_query(db: Session, req: QueryRequest, request: Request):
    """SSE live progress retrieval, context, rồi answer delta."""
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    sequence = 0
    current_stage = "normalize"
    current_detail: dict = {}

    async def on_progress(event: dict) -> None:
        nonlocal current_stage, current_detail
        next_stage = event.get("stage", current_stage)
        if next_stage != current_stage:
            current_detail = {}
        current_stage = next_stage
        current_detail = event.get("detail") or current_detail
        await queue.put(event)

    with tracing.span(
        "playground_query",
        span_type=tracing.CHAIN,
        inputs={"question": req.question},
        attributes={"top_k": req.top_k, "stream": True},
    ) as root:
        retrieval_task = asyncio.create_task(
            _retrieve(req.question, req.top_k, progress=on_progress)
        )
        try:
            yield _sse({"type": "run_started", "run_id": run_id, "question": req.question})
            last_emit = time.perf_counter()
            while not retrieval_task.done() or not queue.empty():
                if await request.is_disconnected():
                    retrieval_task.cancel()
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    if time.perf_counter() - last_emit >= 15:
                        yield ": ping\n\n"
                        last_emit = time.perf_counter()
                    continue
                sequence += 1
                yield _sse(_progress_event(
                    event, run_id=run_id, pipeline="playground", seq=sequence, started=started
                ))
                last_emit = time.perf_counter()

            citations, graph_facts, coverage = await retrieval_task
            catalogs = _fetch_catalogs(db, citations)
            yield _sse({"type": "catalogs", "catalogs": [c.model_dump() for c in catalogs]})
            yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})
            yield _sse({"type": "graph_facts", "graph_facts": [f.model_dump() for f in graph_facts]})
            yield _sse({"type": "coverage", "subgoals": [s.model_dump() for s in coverage]})
            sequence += 1
            generation_started = time.perf_counter()
            current_stage = "generate"
            yield _sse(_progress_event(
                {"stage": "generate", "status": "started", "label": "Đang soạn câu trả lời"},
                run_id=run_id, pipeline="playground", seq=sequence, started=started,
            ))
            with tracing.span("generate_answer", span_type=tracing.LLM) as gen:
                token_count = 0
                async for delta in llm_client.chat_stream_async(
                    _build_messages(req.question, citations, catalogs, coverage, graph_facts),
                    temperature=0.2, max_tokens=4096, tag="qa_stream",
                ):
                    if await request.is_disconnected():
                        return
                    token_count += 1
                    yield _sse({"type": "token", "content": delta})
                tracing.set_outputs(gen, {"token_deltas": token_count})
            sequence += 1
            yield _sse(_progress_event(
                {
                    "stage": "generate", "status": "completed", "label": "Đã soạn xong câu trả lời",
                    "duration_ms": max(0, round((time.perf_counter() - generation_started) * 1000)),
                },
                run_id=run_id, pipeline="playground", seq=sequence, started=started,
            ))
            tracing.set_outputs(root, {"num_citations": len(citations), "num_graph_facts": len(graph_facts)})
        except asyncio.CancelledError:
            retrieval_task.cancel()
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stream lỗi")
            sequence += 1
            yield _sse(_progress_event(
                {
                    "stage": current_stage, "status": "failed",
                    "label": f"Lỗi tại bước {current_stage}",
                    "detail": {**current_detail, "reason": type(exc).__name__},
                },
                run_id=run_id, pipeline="playground", seq=sequence, started=started,
            ))
            yield _sse({"type": "error", "message": _safe_error_message(current_stage)})
        finally:
            if not retrieval_task.done():
                retrieval_task.cancel()
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
        graph_facts=result.graph_facts,
        normalized_question=result.normalized_question,
        rewritten_question=result.rewritten_question,
        tool_calls=result.tool_calls,
        subgoals=result.subgoals,
        config=config,
    )


@router.post("/mcp-retrieve/stream")
async def mcp_retrieve_stream(
    req: McpRetrieveRequest, request: Request, db: Session = Depends(get_db)
):
    return StreamingResponse(
        _stream_mcp_retrieve(db, req, request), media_type="text/event-stream", headers=SSE_HEADERS
    )


async def _stream_mcp_retrieve(db: Session, req: McpRetrieveRequest, request: Request):
    run_id = str(uuid.uuid4())
    started = time.perf_counter()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    sequence = 0
    current_stage = "normalize"
    current_detail: dict = {}

    async def on_progress(event: dict) -> None:
        nonlocal current_stage, current_detail
        next_stage = event.get("stage", current_stage)
        if next_stage != current_stage:
            current_detail = {}
        current_stage = next_stage
        current_detail = event.get("detail") or current_detail
        await queue.put(event)

    task = asyncio.create_task(retrieval_client.retrieve(req.question, req.top_k, progress=on_progress))
    try:
        yield _sse({"type": "run_started", "run_id": run_id, "question": req.question})
        last_emit = time.perf_counter()
        while not task.done() or not queue.empty():
            if await request.is_disconnected():
                task.cancel()
                return
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except TimeoutError:
                if time.perf_counter() - last_emit >= 15:
                    yield ": ping\n\n"
                    last_emit = time.perf_counter()
                continue
            sequence += 1
            yield _sse(_progress_event(
                event, run_id=run_id, pipeline="mcp", seq=sequence, started=started
            ))
            last_emit = time.perf_counter()
        result = await task
        config = McpRetrieveConfig(
            normalize=settings.retrieval_enable_normalize,
            rewrite=settings.retrieval_enable_rewrite,
            rerank=settings.retrieval_enable_rerank,
            agent_max_steps=settings.retrieval_agent_max_steps,
        )
        yield _sse({
            "type": "retrieve_result",
            **result.model_dump(),
            "config": config.model_dump(),
        })
        catalogs = _fetch_catalogs(db, result.citations)
        current_stage = "generate"
        generation_started = time.perf_counter()
        sequence += 1
        yield _sse(_progress_event(
            {"stage": "generate", "status": "started", "label": "Đang soạn câu trả lời"},
            run_id=run_id, pipeline="mcp", seq=sequence, started=started,
        ))
        async for delta in llm_client.chat_stream_async(
            _build_messages(
                req.question, result.citations, catalogs, result.subgoals, result.graph_facts
            ),
            temperature=0.2, max_tokens=4096, tag="mcp_playground_stream",
        ):
            if await request.is_disconnected():
                return
            yield _sse({"type": "token", "content": delta})
        sequence += 1
        yield _sse(_progress_event(
            {
                "stage": "generate", "status": "completed", "label": "Đã soạn xong câu trả lời",
                "duration_ms": max(0, round((time.perf_counter() - generation_started) * 1000)),
            },
            run_id=run_id, pipeline="mcp", seq=sequence, started=started,
        ))
    except asyncio.CancelledError:
        task.cancel()
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("MCP retrieve stream lỗi")
        sequence += 1
        yield _sse(_progress_event(
            {
                "stage": current_stage, "status": "failed",
                "label": f"Lỗi tại bước {current_stage}",
                "detail": {**current_detail, "reason": type(exc).__name__},
            },
            run_id=run_id, pipeline="mcp", seq=sequence, started=started,
        ))
        yield _sse({"type": "error", "message": _safe_error_message(current_stage)})
    finally:
        if not task.done():
            task.cancel()
    yield "data: [DONE]\n\n"
