"""Test RAG technique registry (FR-17) — offline, monkeypatch qa_service.answer."""
import pytest

from app.schemas.playground import Citation
from app.services import qa_service
from eval.techniques import resolve


def test_registry_resolves_trivial(monkeypatch):
    c1 = Citation(document_id="d1", title="T", chunk_index=0, score=0.9, final_content="ND1")
    c2 = Citation(document_id="d1", title="T", chunk_index=1, score=0.8, final_content="ND2")

    def fake_answer(question, top_k):
        assert question == "Phí?"
        assert top_k == 5
        return "trả lời", [c1, c2]

    monkeypatch.setattr(qa_service, "answer", fake_answer)

    technique = resolve("trivial")
    response, contexts = technique("Phí?", 5)

    assert response == "trả lời"
    assert contexts == ["ND1", "ND2"]


def test_unknown_technique_rejected():
    with pytest.raises(ValueError, match="trivial"):
        resolve("foo")
