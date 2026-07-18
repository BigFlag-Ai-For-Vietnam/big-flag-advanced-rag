"""Ingest 10 PDF compliance (sample_compliance_corpus/) qua ĐÚNG pipeline app thật —
parsing (VLM) -> chunking (contextual) -> catalog -> embed + Qdrant. Không sửa 1 dòng
app/services/pipeline.py — gọi thẳng run_pipeline() đồng bộ (không qua HTTP/BackgroundTasks)
để script chờ xong từng document rồi in tiến độ.

Dùng collection Qdrant RIÊNG cho corpus này — set qua env var TRƯỚC khi chạy script
(không sửa qdrant_service.py/config.py):

    cd backend
    QDRANT_COLLECTION=rag_chunks_compliance python -m poc.kg_ontology.ingest_corpus
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.config import settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Document, DocumentStatus  # noqa: E402
from app.services import pipeline, storage_service  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parents[3] / "sample_compliance_corpus"
CATEGORY = "tuan_thu"


def _iter_pdfs() -> list[Path]:
    return sorted(CORPUS_DIR.glob("*.pdf"))


def main() -> None:
    if not settings.fpt_api_key:
        raise SystemExit("FPT_API_KEY chưa cấu hình (.env).")
    pdfs = _iter_pdfs()
    if not pdfs:
        raise SystemExit(f"Không tìm thấy PDF nào ở {CORPUS_DIR}")
    print(f"Qdrant collection: {settings.qdrant_collection}")
    print(f"Sẽ ingest {len(pdfs)} PDF từ {CORPUS_DIR}")

    init_db()
    db = SessionLocal()
    try:
        results = []
        for i, pdf_path in enumerate(pdfs, start=1):
            title = pdf_path.stem
            print(f"\n[{i}/{len(pdfs)}] {pdf_path.name}")

            document_id_row = Document(
                title=title,
                original_filename=pdf_path.name,
                file_path="",  # set ngay dưới sau khi có id
                status=DocumentStatus.uploaded,
                category=CATEGORY,
            )
            db.add(document_id_row)
            db.flush()  # có .id nhưng chưa commit, dùng để đặt storage key

            file_key = storage_service.put_bytes(
                f"uploads/{document_id_row.id}.pdf", pdf_path.read_bytes()
            )
            document_id_row.file_path = file_key
            db.commit()
            db.refresh(document_id_row)

            pipeline.run_pipeline(document_id_row.id)

            db.refresh(document_id_row)
            status = document_id_row.status
            chunk_count = len(document_id_row.chunks)
            catalog_facets = len((document_id_row.catalog or {}).get("tree", []))
            print(
                f"    -> status={status.value} chunks={chunk_count} "
                f"catalog_facets={catalog_facets} doc_id={document_id_row.id}"
            )
            if status != DocumentStatus.indexed:
                print(f"    !! KHÔNG indexed: {document_id_row.error_message}")
            results.append((title, document_id_row.id, status.value, chunk_count, catalog_facets))

        print("\n=== Tổng kết ===")
        ok = sum(1 for r in results if r[2] == "indexed")
        print(f"{ok}/{len(results)} document indexed thành công.")
        for title, doc_id, status, chunks, facets in results:
            print(f"  {status:10s} chunks={chunks:2d} facets={facets:2d}  {title}  ({doc_id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
