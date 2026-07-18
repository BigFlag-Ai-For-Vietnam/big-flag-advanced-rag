"""SSE Playground: progress phải đến trước context và answer delta."""
import asyncio
import json

from app.routers import playground
from app.schemas.playground import Citation, McpRetrieveRequest, QueryRequest, RetrieveResult


class ConnectedRequest:
    async def is_disconnected(self):
        return False


def _event(chunk: str):
    if not chunk.startswith("data: {"):
        return None
    return json.loads(chunk.removeprefix("data: ").strip())


def test_stream_orders_progress_before_context_and_tokens(monkeypatch):
    citation = Citation(document_id="d1", title="Doc", chunk_index=0, score=0.9, final_content="ctx")

    async def fake_retrieve(_question, _top_k, *, progress=None):
        await progress({"stage": "plan", "status": "completed", "label": "Đã lập kế hoạch"})
        return [citation], [], []

    async def fake_stream(_messages, **_kwargs):
        yield "xin "
        yield "chào"

    monkeypatch.setattr(playground, "_retrieve", fake_retrieve)
    monkeypatch.setattr(playground, "_fetch_catalogs", lambda _db, _citations: [])
    monkeypatch.setattr(playground.llm_client, "chat_stream_async", fake_stream)

    async def collect():
        req = QueryRequest(question="q", stream=True)
        return [chunk async for chunk in playground._stream_query(object(), req, ConnectedRequest())]

    events = [event for event in map(_event, asyncio.run(collect())) if event]
    types = [event["type"] for event in events]
    assert types.index("progress") < types.index("citations") < types.index("token")
    assert [event["content"] for event in events if event["type"] == "token"] == ["xin ", "chào"]
    assert events[-1]["type"] == "progress"
    assert events[-1]["stage"] == "generate"


def test_mcp_stream_generates_answer_after_retrieval(monkeypatch):
    citation = Citation(document_id="d1", title="Doc", chunk_index=0, score=0.9, final_content="ctx")

    async def fake_retrieve(_question, _top_k, *, progress=None):
        await progress({"stage": "finalize", "status": "completed", "label": "Đã tổng hợp"})
        return RetrieveResult(
            citations=[citation], graph_facts=[], normalized_question="q",
            rewritten_question="q rewrite", tool_calls=[], subgoals=[],
        )

    async def fake_stream(_messages, **_kwargs):
        yield "câu "
        yield "trả lời"

    monkeypatch.setattr(playground.retrieval_client, "retrieve", fake_retrieve)
    monkeypatch.setattr(playground, "_fetch_catalogs", lambda _db, _citations: [])
    monkeypatch.setattr(playground.llm_client, "chat_stream_async", fake_stream)

    async def collect():
        req = McpRetrieveRequest(question="q")
        return [
            chunk async for chunk in playground._stream_mcp_retrieve(
                object(), req, ConnectedRequest()
            )
        ]

    events = [item for item in map(_event, asyncio.run(collect())) if item]
    types = [item["type"] for item in events]
    assert types.index("retrieve_result") < types.index("token")
    assert [item["content"] for item in events if item["type"] == "token"] == ["câu ", "trả lời"]
    assert events[-1]["type"] == "progress"
    assert events[-1]["stage"] == "generate"
    assert events[-1]["status"] == "completed"
