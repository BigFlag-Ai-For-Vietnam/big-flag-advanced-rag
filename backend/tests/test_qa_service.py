"""Test dịch vụ QA dùng chung (FR-11) — offline, monkeypatch retrieval/LLM."""
from app.schemas.playground import Citation
from app.services import qa_service


def test_retrieve_field_mapping(monkeypatch):
    monkeypatch.setattr(qa_service.embedding_service, "embed_query", lambda q: [0.0])
    monkeypatch.setattr(
        qa_service.qdrant_service,
        "search",
        lambda vec, top_k: [
            {"id": "p1", "score": 0.9, "payload": {
                "document_id": "d1", "title": "T", "chunk_index": 2, "final_content": "c1"
            }}
        ],
    )
    result = qa_service.retrieve("q", 5)
    assert result == [
        Citation(document_id="d1", title="T", chunk_index=2, score=0.9, final_content="c1")
    ]


def test_messages_identical_to_playground():
    citations = [
        Citation(document_id="d1", title="Tài liệu A", chunk_index=0, score=0.5, final_content="nội dung 1"),
        Citation(document_id="d1", title="Tài liệu A", chunk_index=1, score=0.4, final_content="nội dung 2"),
    ]
    messages = qa_service.build_messages("Câu hỏi?", citations)
    assert messages[0] == {"role": "system", "content": qa_service.SYSTEM_PROMPT}
    user_content = messages[1]["content"]
    assert "[1] (Tài liệu: Tài liệu A, đoạn #0)\nnội dung 1" in user_content
    assert "[2] (Tài liệu: Tài liệu A, đoạn #1)\nnội dung 2" in user_content
    assert "CÂU HỎI: Câu hỏi?" in user_content

    empty_messages = qa_service.build_messages("Câu hỏi?", [])
    assert "(không có ngữ cảnh)" in empty_messages[1]["content"]
