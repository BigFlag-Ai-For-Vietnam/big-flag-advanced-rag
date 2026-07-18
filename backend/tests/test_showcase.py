"""Showcase comparison tests — offline, không gọi FPT/Qdrant/MCP thật."""
import asyncio
import json

from pydantic import ValidationError

from app.routers import showcase
from app.schemas.playground import (
    Citation,
    GraphFact,
    RetrieveResult,
    ShowcaseCompareRequest,
    SubgoalCoverage,
)


def _drain_worker(worker):
    async def run():
        queue = asyncio.Queue()
        await worker(queue)
        events = []
        while not queue.empty():
            events.append(await queue.get())
        return events

    return asyncio.run(run())


def test_showcase_request_validation():
    assert ShowcaseCompareRequest(question="q").top_k == 5
    try:
        ShowcaseCompareRequest(question="", top_k=5)
        assert False, "empty question must fail"
    except ValidationError:
        pass
    try:
        ShowcaseCompareRequest(question="q", top_k=21)
        assert False, "top_k > 20 must fail"
    except ValidationError:
        pass


def test_raw_pipeline_is_dense_only_and_streams(monkeypatch):
    citation = Citation(
        document_id="d1", title="Doc", chunk_index=1, score=0.8, final_content="evidence"
    )
    calls = []

    def fake_retrieve(question, top_k):
        calls.append((question, top_k))
        return [citation]

    async def fake_stream(messages, **kwargs):
        assert "CÂU HỎI: câu hỏi" in messages[1]["content"]
        assert kwargs["temperature"] == 0.2
        assert kwargs["max_tokens"] == 1024
        yield "câu "
        yield "trả lời"

    monkeypatch.setattr(showcase.qa_service, "retrieve", fake_retrieve)
    monkeypatch.setattr(showcase.llm_client, "chat_stream_async", fake_stream)
    req = ShowcaseCompareRequest(question="câu hỏi", top_k=3)

    events = _drain_worker(
        lambda queue: showcase._run_raw(req, queue, showcase.time.perf_counter())
    )
    payloads = [payload for payload, _terminal in events]

    assert calls == [("câu hỏi", 3)]
    assert [p["type"] for p in payloads] == [
        "pipeline_context", "pipeline_token", "pipeline_token", "pipeline_done"
    ]
    assert payloads[0]["pipeline"] == "raw"
    assert payloads[0]["trace"][1]["stage"] == "qdrant"
    assert payloads[-1]["citation_count"] == 1
    assert events[-1][1] is True


def test_advanced_pipeline_exposes_trace_and_coverage(monkeypatch):
    citation = Citation(
        document_id="d1", title="Doc", chunk_index=1, score=0.9, final_content="evidence"
    )
    coverage = SubgoalCoverage(
        description="tìm quy định", query="quy định", satisfied=True, evidence_count=1
    )
    graph_fact = GraphFact(
        fact_id="f1",
        source_entity="QĐ342",
        source_type="Document",
        relation="THAY_THE",
        target_entity="QĐ215",
        target_type="Document",
    )
    result = RetrieveResult(
        citations=[citation],
        graph_facts=[graph_fact],
        normalized_question="q",
        rewritten_question="q rõ hơn",
        tool_calls=[{"tool": "query_vector_store", "args": {"query": "q"}, "hit_count": 1}],
        subgoals=[coverage],
    )

    async def fake_retrieve(question, top_k):
        return result

    async def fake_stream(_messages, **_kwargs):
        yield "answer"

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(showcase.retrieval_client, "retrieve", fake_retrieve)
    monkeypatch.setattr(showcase, "SessionLocal", FakeSession)
    monkeypatch.setattr(showcase.qa_service, "fetch_catalogs", lambda db, citations: [])
    monkeypatch.setattr(showcase.llm_client, "chat_stream_async", fake_stream)
    req = ShowcaseCompareRequest(question="q", top_k=5)

    events = _drain_worker(
        lambda queue: showcase._run_advanced(req, queue, showcase.time.perf_counter())
    )
    context = events[0][0]

    assert context["pipeline"] == "advanced"
    assert context["rewritten_question"] == "q rõ hơn"
    assert context["tool_calls"][0]["tool"] == "query_vector_store"
    assert context["subgoals"][0]["satisfied"] is True
    assert context["graph_facts"][0]["relation"] == "THAY_THE"
    assert events[-1][0]["type"] == "pipeline_done"
    assert events[-1][0]["graph_fact_count"] == 1


def test_compare_stream_keeps_other_pipeline_alive_after_error(monkeypatch):
    async def failed(_req, queue, _started):
        await showcase._emit(
            queue,
            {"type": "pipeline_error", "pipeline": "advanced", "message": "MCP down"},
            terminal=True,
        )

    async def successful(_req, queue, _started):
        await showcase._emit(
            queue,
            {"type": "pipeline_token", "pipeline": "raw", "content": "ok"},
        )
        await showcase._emit(
            queue,
            {"type": "pipeline_done", "pipeline": "raw", "total_ms": 10},
            terminal=True,
        )

    class ConnectedRequest:
        async def is_disconnected(self):
            return False

    monkeypatch.setattr(showcase, "_run_advanced", failed)
    monkeypatch.setattr(showcase, "_run_raw", successful)

    async def collect():
        req = ShowcaseCompareRequest(question="q", top_k=5)
        return [chunk async for chunk in showcase._compare_stream(req, ConnectedRequest())]

    chunks = asyncio.run(collect())
    events = []
    for chunk in chunks:
        if not chunk.startswith("data: {"):
            continue
        events.append(json.loads(chunk.removeprefix("data: ").strip()))

    assert any(e["type"] == "pipeline_error" and e["pipeline"] == "advanced" for e in events)
    assert any(e["type"] == "pipeline_token" and e["pipeline"] == "raw" for e in events)
    assert any(e["type"] == "pipeline_done" and e["pipeline"] == "raw" for e in events)
    assert events[-1]["type"] == "run_done"
