"""Backfill: sinh lại CATALOG (cây entities) cho document đã xử lý — KHÔNG re-parse VLM.

Dùng khi đổi thuật toán/schema catalog: nạp chunks contextual (hoặc pages theo
`CATALOG_SOURCE`) đã có trong DB rồi gọi `catalog_service.generate_catalog`, ghi đè
`Document.catalog`. Rẻ vì chỉ tốn LLM text (không chạy lại vision/embedding/Qdrant).

Chạy từ thư mục backend (cần .env có FPT_API_KEY + FPT_CHAT_MODEL):
    python -m scripts.recatalog            # tất cả document
    python -m scripts.recatalog <doc_id>   # 1 document
    python -m scripts.recatalog --category van_ban_tuan_thu
        # áp preset compliance + sinh lại catalog cho tất cả document
"""
from __future__ import annotations

import argparse

from app.catalog_presets import CATALOG_PRESETS, resolve_focus_entities
from app.config import settings
from app.db import SessionLocal
from app.models import Document
from app.services import catalog_service


def _catalog_input(doc: Document) -> tuple[list[str], str, str]:
    """Lấy đúng nguồn catalog giống pipeline và full text làm fallback."""
    page_texts = [p.parsed_text or "" for p in doc.pages]
    full_text = "\n\n".join(t for t in page_texts if t.strip())
    if settings.catalog_source == "pages":
        return page_texts, "page", full_text
    return [c.final_content for c in doc.chunks], "chunk", full_text


def _recatalog_one(db, doc: Document, category: str | None = None) -> int:
    if category:
        # Ghi lại config để lần reprocess sau tiếp tục dùng đúng preset đã chọn.
        doc.category = category
        doc.focus_entities = resolve_focus_entities(category, None)

    focus = doc.focus_entities or resolve_focus_entities(doc.category, None)
    unit_texts, unit_kind, full_text = _catalog_input(doc)
    doc.catalog = catalog_service.generate_catalog(
        doc.title,
        unit_texts,
        focus,
        unit_kind=unit_kind,
        full_text_fallback=full_text,
    )
    db.commit()
    return len(doc.catalog.get("tree", []))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id", nargs="?", help="UUID document; bỏ trống để xử lý tất cả.")
    ap.add_argument(
        "--category",
        choices=tuple(CATALOG_PRESETS),
        help="Gán preset này vào document trước khi sinh lại catalog.",
    )
    args = ap.parse_args()

    db = SessionLocal()
    try:
        docs = [db.get(Document, args.doc_id)] if args.doc_id else db.query(Document).all()
        docs = [d for d in docs if d is not None]
        if not docs:
            print("Không tìm thấy document nào.")
            return
        for doc in docs:
            unit_texts, unit_kind, full_text = _catalog_input(doc)
            if not any(text.strip() for text in unit_texts) and not full_text.strip():
                print(f"[skip] '{doc.title}' chưa có {unit_kind} để sinh catalog.")
                continue
            n = _recatalog_one(db, doc, args.category)
            category_note = f", preset={args.category}" if args.category else ""
            print(
                f"[ok] '{doc.title}' -> {n} facet gốc "
                f"({len(unit_texts)} {unit_kind}{category_note})."
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
