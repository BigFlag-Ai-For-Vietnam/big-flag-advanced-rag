"""Test tool cho react subgraph (không gọi API ngoài — mock embedding_service/qdrant_service)."""
from app.retrieval.tools import query_graph_knowledge, query_vector_store
from app.services import embedding_service, qdrant_service


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


def test_query_graph_knowledge_stub_returns_empty():
    assert query_graph_knowledge.invoke({"query": "quan hệ giữa thẻ A và thẻ B"}) == []
