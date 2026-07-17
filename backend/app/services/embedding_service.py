"""Bước C helper — embed final_content theo batch qua FPT embeddings API."""
from __future__ import annotations

from app.services import llm_client


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed danh sách text theo batch để tránh payload quá lớn."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(llm_client.embed(batch, tag="embed_index"))
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed 1 câu hỏi cho retrieval."""
    return llm_client.embed([text], tag="embed_query")[0]
