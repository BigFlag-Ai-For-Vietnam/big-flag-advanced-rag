"""Bước C helper — embed final_content theo batch qua FPT embeddings API."""
from __future__ import annotations

from app.config import settings
from app.services import llm_client, tracing


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed danh sách text theo batch để tránh payload quá lớn."""
    num_batches = (len(texts) + batch_size - 1) // batch_size
    with tracing.span(
        "embed_texts",
        span_type=tracing.EMBEDDING,
        inputs={"num_texts": len(texts), "batch_size": batch_size},
        attributes={
            "model": settings.fpt_embed_model,
            "embed_dim": settings.embed_dim,
            "num_batches": num_batches,
        },
    ) as span:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            vectors.extend(llm_client.embed(batch, tag="embed_index"))
        tracing.set_outputs(span, {"num_vectors": len(vectors)})
        return vectors


def embed_query(text: str) -> list[float]:
    """Embed 1 câu hỏi cho retrieval."""
    with tracing.span(
        "embed_query",
        span_type=tracing.EMBEDDING,
        inputs={"chars": len(text)},
        attributes={"model": settings.fpt_embed_model, "embed_dim": settings.embed_dim},
    ) as span:
        vec = llm_client.embed([text], tag="embed_query")[0]
        tracing.set_outputs(span, {"dim": len(vec)})
        return vec
