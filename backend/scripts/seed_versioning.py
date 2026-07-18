"""Seed metadata versioning (doc_no / version_label / effective_date) cho bộ corpus mô phỏng
đã ingest — KHÔNG re-ingest (không tốn token FPT). Chỉ ghi cột versioning lên Document có sẵn.

Khớp document theo tên file (original_filename) hoặc title. Nếu ingest bộ
`sample_compliance_corpus/` (tên file giữ nguyên) thì khớp tự động.

Chạy từ thư mục backend (cần .env có DB_URL + QDRANT_URL trỏ đúng — localhost khi chạy trên host):
    python -m scripts.seed_versioning            # set doc_no + effective_date cho 10 văn bản
    python -m scripts.seed_versioning --wire-215 # + set sẵn quan hệ QĐ 215 bị 342 thay thế (demo timeline chạy ngay)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.db import SessionLocal, init_db
from app.models import Document
from app.services import qdrant_service


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


# match: token duy nhất xuất hiện trong tên file/title của từng văn bản trong corpus mô phỏng.
SEED = [
    {"key": "01_nd_88",  "doc_no": "88/2024/NĐ-CP",    "version": None,  "eff": _dt(2025, 1, 1)},
    {"key": "02_tt_09",  "doc_no": "09/2024/TT-NHNN",  "version": None,  "eff": _dt(2024, 7, 1)},
    {"key": "03_tt_04",  "doc_no": "04/2025/TT-NHNN",  "version": None,  "eff": _dt(2025, 6, 1)},
    {"key": "04_qd_215", "doc_no": "215/2022/QĐ-DDB",  "version": "v1.0", "eff": _dt(2022, 3, 10)},
    {"key": "05_qd_342", "doc_no": "342/2024/QĐ-DDB",  "version": "v2.0", "eff": _dt(2024, 9, 1)},
    {"key": "06_qd_401", "doc_no": "401/2024/QĐ-DDB",  "version": None,  "eff": _dt(2024, 12, 1)},
    {"key": "07_qd_455", "doc_no": "455/2025/QĐ-DDB",  "version": None,  "eff": _dt(2025, 3, 1)},
    {"key": "08_qd_502", "doc_no": "502/2025/QĐ-DDB",  "version": None,  "eff": _dt(2025, 6, 1)},
    {"key": "09_tt_20",  "doc_no": "20/2024/TT-NHNN",  "version": None,  "eff": _dt(2024, 9, 1)},
    {"key": "10_qd_480", "doc_no": "480/2025/QĐ-DDB",  "version": None,  "eff": _dt(2025, 5, 1)},
]


def _match(doc: Document, key: str) -> bool:
    hay = f"{doc.original_filename or ''} {doc.title or ''}".lower()
    return key in hay


def _find(db, key: str) -> Document | None:
    for doc in db.query(Document).all():
        if _match(doc, key):
            return doc
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wire-215", action="store_true",
                    help="Set sẵn quan hệ QĐ 215 bị QĐ 342 thay thế (is_active=false + link).")
    args = ap.parse_args()

    init_db()  # đảm bảo cột versioning tồn tại (idempotent) kể cả khi backend chưa restart
    db = SessionLocal()
    try:
        by_key: dict[str, Document] = {}
        for row in SEED:
            doc = _find(db, row["key"])
            if doc is None:
                print(f"[skip] chưa ingest '{row['key']}' ({row['doc_no']}).")
                continue
            doc.doc_no = row["doc_no"]
            doc.version_label = row["version"]
            doc.effective_date = row["eff"]
            if doc.is_active is None:
                doc.is_active = True
            by_key[row["key"]] = doc
            print(f"[ok] '{doc.title}' -> doc_no={row['doc_no']} eff={row['eff'].date()}")
        db.commit()

        if args.wire_215:
            old = by_key.get("04_qd_215")
            new = by_key.get("05_qd_342")
            if old is None or new is None:
                print("[wire-215] cần cả QĐ 215 và QĐ 342 đã ingest — bỏ qua.")
            else:
                old.is_active = False
                old.expiry_date = new.effective_date
                old.superseded_by_id = new.id
                old.supersession_note = "Giữ hiệu lực Phụ lục 02 (Danh mục hệ thống trọng yếu)."
                new.supersedes_id = old.id
                db.commit()
                try:
                    qdrant_service.set_active(old.id, False)
                except Exception as exc:  # noqa: BLE001 — Qdrant có thể chưa reachable trên host
                    print(f"[wire-215] cảnh báo: không cập nhật được Qdrant is_active ({exc}). "
                          f"Chạy reprocess QĐ 215 hoặc đảm bảo QDRANT_URL đúng.")
                print(f"[wire-215] QĐ 215 bị QĐ 342 thay thế (is_active=false).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
