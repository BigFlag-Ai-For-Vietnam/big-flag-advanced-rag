"""Test outer graph engine: normalize -> rewrite -> react subgraph -> rerank.

Không gọi FPT thật — tiêm fake BaseChatModel vào engine.build_graph(model=...), chỉ
mock embedding_service/qdrant_service (dùng thật bởi tool query_vector_store).
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import settings
from app.retrieval import engine
from app.services import embedding_service, qdrant_service


def _make_fake_model(responses: list[AIMessage]) -> BaseChatModel:
    """Model giả trả lần lượt các AIMessage đã định sẵn (lặp lại cái cuối nếu gọi quá số lượng)."""
    state = {"i": 0}

    class _Fake(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "fake"

        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return self.bind(tools=tools)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            idx = min(state["i"], len(responses) - 1)
            state["i"] += 1
            return ChatResult(generations=[ChatGeneration(message=responses[idx])])

    return _Fake()


def _mock_vector_store(monkeypatch):
    monkeypatch.setattr(embedding_service, "embed_query", lambda text: [0.1])
    monkeypatch.setattr(
        qdrant_service,
        "search",
        lambda vector, top_k: [
            {
                "id": "p1",
                "score": 0.8,
                "payload": {
                    "chunk_id": "c1",
                    "document_id": "d1",
                    "title": "Thẻ tín dụng Sung Túc",
                    "chunk_index": 0,
                    "final_content": "Phí thường niên 500.000đ.",
                },
            }
        ],
    )


def test_engine_runs_normalize_rewrite_react_rerank_in_order(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_normalize", True)
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", False)  # đã test riêng ở test_retrieval_nodes.py
    monkeypatch.setattr(settings, "retrieval_enable_rerank", True)
    monkeypatch.setattr(settings, "retrieval_agent_max_steps", 10)
    _mock_vector_store(monkeypatch)

    fake_model = _make_fake_model(
        [
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="query_vector_store", args={"query": "phí thường niên", "top_k": 3}, id="tc1", type="tool_call")],
            ),
            AIMessage(content="đã tìm xong", tool_calls=[]),
        ]
    )

    graph = engine.build_graph(model=fake_model)
    result = graph.invoke({"question": "  phí   thường niên  ", "top_k": 3, "messages": []})

    assert result["normalized_question"] == "phí thường niên"
    assert result["rewritten_question"] == "phí thường niên"  # rewrite tắt -> passthrough
    assert len(result["citations"]) == 1
    assert result["citations"][0].final_content == "Phí thường niên 500.000đ."
    assert result["citations"][0].document_id == "d1"


def test_engine_stops_gracefully_without_exceeding_recursion_limit(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_normalize", True)
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", False)
    monkeypatch.setattr(settings, "retrieval_enable_rerank", True)
    monkeypatch.setattr(settings, "retrieval_agent_max_steps", 4)  # giới hạn thấp
    _mock_vector_store(monkeypatch)

    # Model "cứng đầu": luôn gọi lại tool, không bao giờ tự dừng -> phải test recursion_limit chặn được.
    always_call_tool = _make_fake_model(
        [
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="query_vector_store", args={"query": "x"}, id="tc-repeat", type="tool_call")],
            )
        ]
    )

    graph = engine.build_graph(model=always_call_tool)
    # Không được raise GraphRecursionError ra ngoài, phải dừng và vẫn có citations từ tool đã gọi được.
    result = graph.invoke({"question": "câu hỏi lặp vô hạn", "top_k": 5, "messages": []})

    assert isinstance(result["citations"], list)
    assert len(result["citations"]) >= 1
