"""Test node deterministic của outer graph: normalize/rewrite/rerank + toggle bật/tắt
(không gọi API ngoài — mock llm_client.chat)."""
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.config import settings
from app.retrieval import nodes


def test_normalize_collapses_whitespace(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_normalize", True)
    assert nodes.normalize("  phí   thường  niên   là gì  ") == "phí thường niên là gì"


def test_normalize_disabled_is_passthrough(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_normalize", False)
    raw = "  phí   thường niên  "
    assert nodes.normalize(raw) == raw


def test_rewrite_calls_llm_and_returns_text(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", True)
    monkeypatch.setattr(nodes.llm_client, "chat", lambda messages, **kw: "Phí thường niên thẻ Sung Túc là bao nhiêu?")
    assert nodes.rewrite("phí thường niên bao nhiêu") == "Phí thường niên thẻ Sung Túc là bao nhiêu?"


def test_rewrite_disabled_is_passthrough_without_llm_call(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", False)

    def _boom(*args, **kwargs):
        raise AssertionError("không được gọi llm_client.chat khi rewrite tắt")

    monkeypatch.setattr(nodes.llm_client, "chat", _boom)
    assert nodes.rewrite("câu hỏi gốc") == "câu hỏi gốc"


def test_rewrite_falls_back_to_question_on_empty_llm_output(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", True)
    monkeypatch.setattr(nodes.llm_client, "chat", lambda messages, **kw: "   ")
    assert nodes.rewrite("câu hỏi gốc") == "câu hỏi gốc"


def _tool_message(chunks: list[dict]) -> ToolMessage:
    return ToolMessage(content=json.dumps(chunks, ensure_ascii=False), tool_call_id="tc1")


def test_rerank_dedupes_across_tool_calls_and_sorts_by_score(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_rerank", True)
    messages = [
        HumanMessage(content="câu hỏi"),
        AIMessage(content="", tool_calls=[]),
        _tool_message(
            [
                {"chunk_id": "c1", "document_id": "d1", "title": "T1", "chunk_index": 0, "score": 0.5, "final_content": "a"},
                {"chunk_id": "c2", "document_id": "d1", "title": "T1", "chunk_index": 1, "score": 0.9, "final_content": "b"},
            ]
        ),
        _tool_message(
            [
                # c1 trùng chunk_id với lần gọi trước -> phải dedupe, giữ bản đầu tiên
                {"chunk_id": "c1", "document_id": "d1", "title": "T1", "chunk_index": 0, "score": 0.5, "final_content": "a"},
                {"chunk_id": "c3", "document_id": "d2", "title": "T2", "chunk_index": 0, "score": 0.7, "final_content": "c"},
            ]
        ),
    ]

    citations = nodes.rerank(messages, top_k=2)

    assert [c.final_content for c in citations] == ["b", "c"]  # score 0.9, 0.7 — c1 (0.5) bị cắt vì top_k=2


def test_rerank_disabled_skips_sort_but_still_dedupes(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_rerank", False)
    messages = [
        _tool_message(
            [
                {"chunk_id": "c1", "document_id": "d1", "title": "T1", "chunk_index": 0, "score": 0.1, "final_content": "first"},
                {"chunk_id": "c2", "document_id": "d1", "title": "T1", "chunk_index": 1, "score": 0.99, "final_content": "second"},
                {"chunk_id": "c1", "document_id": "d1", "title": "T1", "chunk_index": 0, "score": 0.1, "final_content": "first"},
            ]
        ),
    ]

    citations = nodes.rerank(messages, top_k=10)

    # giữ thứ tự xuất hiện (không sort theo score) sau khi dedupe
    assert [c.final_content for c in citations] == ["first", "second"]


def test_rerank_ignores_non_tool_messages():
    messages = [HumanMessage(content="hi"), AIMessage(content="ok")]
    assert nodes.rerank(messages, top_k=5) == []
