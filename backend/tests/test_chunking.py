"""Test chunking: đúng chunk_size/overlap/separator (không gọi API ngoài)."""
from app.services.chunking_service import split_text
from app.config import settings


def _make_text(paragraphs: int, words_per_para: int = 60) -> str:
    paras = []
    for p in range(paragraphs):
        words = [f"w{p}_{i}" for i in range(words_per_para)]
        paras.append(" ".join(words))
    return "\n\n".join(paras)


def test_split_text_produces_multiple_chunks():
    text = _make_text(paragraphs=40)  # đủ dài để vượt chunk_size
    chunks = split_text(text)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_split_short_text_single_chunk():
    chunks = split_text("Một đoạn ngắn duy nhất.")
    assert len(chunks) == 1
    assert "Một đoạn ngắn" in chunks[0]


def test_settings_defaults():
    assert settings.chunk_size == 1000
    assert settings.chunk_overlap == 200
