"""Hybrid retrieval: BM25 (keyword/sparse) fuse với dense (Qdrant).

BM25 dựng in-memory từ chunks trong SQLite (retrieval-mcp mount cùng file DB). Với KB
nhỏ (vài chục chunk) đây là cách nhẹ nhất mà vẫn là hybrid thật — vá đúng ca dense yếu:
tra bảng biểu phí / con số / khớp keyword (vd "gói 2", "51 đến 60 tuổi").

fuse(): chuẩn hoá điểm dense & BM25 về [0,1] rồi cộng có trọng số (alpha cho dense).
Không đổi shape kết quả so với query_vector_store (chunk_id/document_id/title/chunk_index/
score/final_content) để engine dùng thẳng.
"""
from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi

from app.config import settings
from app.db import SessionLocal
from app.models import Chunk, Document

logger = logging.getLogger("retrieval.hybrid")

# cache đơn giản: rebuild khi số chunk đổi (index thêm/xoá tài liệu)
_cache: dict = {"count": -1, "bm25": None, "chunks": []}


def _tok(text: str) -> list[str]:
    # tách token: chữ + số, lowercase (giữ số để khớp "51", "60", "2"...)
    return re.findall(r"\w+", (text or "").lower())


def _build_corpus() -> tuple[list[dict], BM25Okapi | None]:
    db = SessionLocal()
    try:
        q = db.query(Chunk, Document.title).join(Document, Chunk.document_id == Document.id)
        if settings.retrieval_exclude_inactive:
            # loại chunk của văn bản đã hết hiệu lực/bị thay thế khỏi corpus BM25
            q = q.filter(Document.is_active.is_(True))
        rows = q.all()
    finally:
        db.close()
    chunks = [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "title": title,
            "chunk_index": c.chunk_index,
            "final_content": c.final_content,
        }
        for c, title in rows
    ]
    bm25 = BM25Okapi([_tok(c["final_content"]) for c in chunks]) if chunks else None
    return chunks, bm25


def _chunk_count() -> int:
    """Đếm chunk làm cache key. Khi loại-bỏ đang bật, chỉ đếm chunk của văn bản còn hiệu lực
    để corpus rebuild ngay khi một văn bản bị thay thế (nếu đếm tất cả, count không đổi → cache cũ)."""
    db = SessionLocal()
    try:
        if settings.retrieval_exclude_inactive:
            return (
                db.query(Chunk)
                .join(Document, Chunk.document_id == Document.id)
                .filter(Document.is_active.is_(True))
                .count()
            )
        return db.query(Chunk).count()
    finally:
        db.close()


def bm25_search(query: str, top_k: int) -> list[dict]:
    """Trả top_k chunk theo BM25 (điểm > 0). Rebuild corpus nếu số chunk đổi."""
    cnt = _chunk_count()
    if _cache["count"] != cnt or _cache["bm25"] is None:
        chunks, bm25 = _build_corpus()
        _cache.update(count=cnt, bm25=bm25, chunks=chunks)
        logger.info("[bm25] rebuild corpus: %s chunks", len(chunks))
    bm25 = _cache["bm25"]
    if bm25 is None:
        return []
    scores = bm25.get_scores(_tok(query))
    ranked = sorted(zip(_cache["chunks"], scores), key=lambda x: x[1], reverse=True)
    return [{**c, "score": float(s)} for c, s in ranked[:top_k] if s > 0]


def _norm(hits: list[dict]) -> dict[str, float]:
    if not hits:
        return {}
    mx = max((h["score"] for h in hits), default=0.0) or 1.0
    return {h["chunk_id"]: h["score"] / mx for h in hits}


def fuse(dense: list[dict], bm25: list[dict], top_k: int, alpha: float = 0.5) -> list[dict]:
    """Hợp nhất dense + BM25: chuẩn hoá [0,1] rồi cộng trọng số (alpha=dense)."""
    dn, bn = _norm(dense), _norm(bm25)
    meta: dict[str, dict] = {h["chunk_id"]: h for h in dense}
    for h in bm25:
        meta.setdefault(h["chunk_id"], h)
    fused = []
    for cid in set(dn) | set(bn):
        score = alpha * dn.get(cid, 0.0) + (1 - alpha) * bn.get(cid, 0.0)
        item = dict(meta[cid])
        item["score"] = round(score, 4)
        fused.append(item)
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]
