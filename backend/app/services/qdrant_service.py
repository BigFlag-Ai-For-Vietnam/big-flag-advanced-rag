"""Tương tác Qdrant: ensure collection, upsert, search, xoá theo document.

Qdrant CHỈ giữ vector + payload nhỏ (document_id, chunk_id, chunk_index, title,
final_content để hiển thị lúc retrieval). Raw text / parse pages nằm ở SQLite.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings

logger = logging.getLogger("qdrant_service")


@lru_cache
def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, timeout=30.0)


def ensure_collection() -> None:
    """Tạo collection nếu chưa có (size=EMBED_DIM, distance=Cosine)."""
    client = _client()
    name = settings.qdrant_collection
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=settings.embed_dim, distance=qm.Distance.COSINE),
    )
    # index payload document_id để filter/delete nhanh
    client.create_payload_index(
        collection_name=name,
        field_name="document_id",
        field_schema=qm.PayloadSchemaType.KEYWORD,
    )
    logger.info("Đã tạo Qdrant collection '%s' (dim=%s)", name, settings.embed_dim)


def upsert_chunks(points: list[dict]) -> None:
    """points: list of {id, vector, payload}. payload nhỏ gọn."""
    if not points:
        return
    ensure_collection()
    client = _client()
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qm.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ],
    )


def search(query_vector: list[float], top_k: int) -> list[dict]:
    """Trả về list {id, score, payload}."""
    ensure_collection()
    client = _client()
    hits = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    ).points
    return [{"id": h.id, "score": h.score, "payload": h.payload or {}} for h in hits]


def delete_by_document(document_id: str) -> None:
    """Xoá toàn bộ points thuộc 1 document."""
    if not _client().collection_exists(settings.qdrant_collection):
        return
    _client().delete(
        collection_name=settings.qdrant_collection,
        points_selector=qm.FilterSelector(
            filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="document_id", match=qm.MatchValue(value=document_id)
                    )
                ]
            )
        ),
    )
