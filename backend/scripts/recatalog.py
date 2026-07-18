"""Backfill: sinh lại CATALOG (cây entities) cho các document đã parse — KHÔNG re-parse VLM.

Dùng khi đổi thuật toán/schema catalog: nạp lại pages đã có trong DB rồi gọi
`catalog_service.generate_catalog`, ghi đè `Document.catalog`. Rẻ vì chỉ tốn LLM text
(không chạy lại vision/embedding/Qdrant).

Chạy từ thư mục backend (cần .env có FPT_API_KEY + FPT_CHAT_MODEL):
    python -m scripts.recatalog            # tất cả document
    python -m scripts.recatalog <doc_id>   # 1 document
"""
from __future__ import annotations

import sys

from app.catalog_presets import resolve_focus_entities
from app.db import SessionLocal
from app.models import Document
from app.services import catalog_service


def _recatalog_one(db, doc: Document) -> int:
    page_texts = [p.parsed_text or "" for p in doc.pages]
    full_text = "\n\n".join(t for t in page_texts if t.strip())
    focus = doc.focus_entities or resolve_focus_entities(doc.category, None)
    doc.catalog = catalog_service.generate_catalog(
        doc.title, page_texts, focus, full_text_fallback=full_text
    )
    db.commit()
    return len(doc.catalog.get("tree", []))


def main() -> None:
    doc_id = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        docs = [db.get(Document, doc_id)] if doc_id else db.query(Document).all()
        docs = [d for d in docs if d is not None]
        if not docs:
            print("Không tìm thấy document nào.")
            return
        for doc in docs:
            if not doc.pages:
                print(f"[skip] '{doc.title}' chưa có pages (chưa parse).")
                continue
            n = _recatalog_one(db, doc)
            print(f"[ok] '{doc.title}' -> {n} facet gốc ({len(doc.pages)} pages).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
