"""Test tool cho react subgraph (không gọi API ngoài — mock embedding_service/qdrant_service/graph_service)."""
from app.config import settings
from app.retrieval.tools import query_graph_knowledge, query_vector_store
from app.services import embedding_service, graph_service, qdrant_service


def test_query_vector_store_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(embedding_service, "embed_query", lambda text: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        qdrant_service,
        "search",
        lambda vector, top_k, active_only=True: [
            {
                "id": "p1",
                "score": 0.9,
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

    results = query_vector_store.invoke({"query": "phí thường niên thẻ Sung Túc", "top_k": 5})

    assert results == [
        {
            "chunk_id": "c1",
            "document_id": "d1",
            "title": "Thẻ tín dụng Sung Túc",
            "chunk_index": 0,
            "score": 0.9,
            "final_content": "Phí thường niên 500.000đ.",
        }
    ]


def test_query_vector_store_empty_hits(monkeypatch):
    monkeypatch.setattr(embedding_service, "embed_query", lambda text: [0.0])
    monkeypatch.setattr(qdrant_service, "search", lambda vector, top_k, active_only=True: [])

    assert query_vector_store.invoke({"query": "câu hỏi bất kỳ"}) == []


def test_query_graph_knowledge_returns_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_graph", False)
    assert query_graph_knowledge.invoke({"query": "quan hệ giữa thẻ A và thẻ B"}) == []


def test_query_graph_knowledge_returns_empty_when_neo4j_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_graph", True)
    monkeypatch.setattr(graph_service, "is_configured", lambda: False)
    assert query_graph_knowledge.invoke({"query": "quan hệ giữa thẻ A và thẻ B"}) == []


def test_query_graph_knowledge_delegates_to_concept_matches(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_graph", True)
    monkeypatch.setattr(graph_service, "is_configured", lambda: True)
    fake_facts = [{"fact_id": "a|AP_DUNG_CHO|b", "source_entity": "a", "relation": "AP_DUNG_CHO", "target_entity": "b"}]
    monkeypatch.setattr(graph_service, "concept_matches", lambda query, top_k: fake_facts)

    results = query_graph_knowledge.invoke({"query": "mật khẩu bao nhiêu ký tự"})

    assert results == fake_facts
