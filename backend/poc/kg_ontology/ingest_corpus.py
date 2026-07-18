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
import os
import sys
import time
from pathlib import Path

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.config import settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Document, DocumentStatus, GraphStatus  # noqa: E402
from app.services import pipeline, storage_service  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parents[3] / "sample_compliance_corpus"
CATEGORY = "van_ban_tuan_thu"


def _iter_pdfs() -> list[Path]:
    return sorted(CORPUS_DIR.glob("*.pdf"))


def _wait_for_graphs(db, document_ids: list[str]) -> dict[str, str]:
    """Giữ process sống tới khi toàn bộ background graph jobs kết thúc."""
    timeout = int(os.environ.get("KG_WAIT_TIMEOUT_SECONDS", "7200"))
    deadline = time.monotonic() + timeout
    last: dict[str, str] = {}
    terminal = {GraphStatus.ready.value, GraphStatus.failed.value}
    while True:
        db.expire_all()
        rows = db.query(Document).filter(Document.id.in_(document_ids)).all()
        current = {
            row.id: (row.graph_status or GraphStatus.not_built.value) for row in rows
        }
        for row in rows:
            if last.get(row.id) != current[row.id]:
                print(f"    [KG] {row.original_filename}: {current[row.id]}")
        last = current
        if len(current) == len(document_ids) and all(v in terminal for v in current.values()):
            return current
        if time.monotonic() >= deadline:
            pending = [doc_id for doc_id, state in current.items() if state not in terminal]
            raise TimeoutError(f"KG build quá {timeout}s; còn chờ document: {pending}")
        time.sleep(2)


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

        graph_results: dict[str, str] = {}
        if settings.kg_enable_build and CATEGORY in settings.kg_categories:
            print("\n=== Chờ Knowledge Graph hoàn tất ===")
            graph_results = _wait_for_graphs(db, [row[1] for row in results])

        print("\n=== Tổng kết ===")
        ok = sum(1 for r in results if r[2] == "indexed")
        print(f"{ok}/{len(results)} document indexed thành công.")
        for title, doc_id, status, chunks, facets in results:
            graph_status = graph_results.get(doc_id, GraphStatus.not_built.value)
            print(
                f"  vector={status:10s} graph={graph_status:10s} chunks={chunks:2d} "
                f"facets={facets:2d}  {title}  ({doc_id})"
            )
        if graph_results:
            graph_ok = sum(1 for value in graph_results.values() if value == GraphStatus.ready.value)
            print(f"{graph_ok}/{len(graph_results)} document build Knowledge Graph thành công.")
            failed_ids = [doc_id for doc_id, value in graph_results.items() if value == GraphStatus.failed.value]
            if failed_ids:
                failed_docs = db.query(Document).filter(Document.id.in_(failed_ids)).all()
                for document in failed_docs:
                    print(f"  KG FAILED {document.original_filename}: {document.graph_error_message}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
