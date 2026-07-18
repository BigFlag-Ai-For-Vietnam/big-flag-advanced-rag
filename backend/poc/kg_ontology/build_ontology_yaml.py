"""Build ontology/entities.yaml + ontology/relations.yaml từ 2 nguồn:

- ground_truth_data.py  (transcribe tay GROUND_TRUTH.md) — NGUỒN CHÍNH cho schema
  (VanBan + thuộc tính, 6 relation type, seed 14 quan hệ + 18 khái niệm).
- Document.catalog của 10 document đã ingest (ingest_corpus.py)  — CHỈ dùng để
  cross-check: mỗi khái niệm ở GROUND_TRUTH §3 có xuất hiện làm node trong cây catalog
  của đúng những document mà GROUND_TRUTH khai "xuất hiện tại" không. Khái niệm không
  match ở bất kỳ đâu được in cảnh báo để soát tay — KHÔNG tự ý bỏ qua.

Chạy (từ backend/, sau khi ingest_corpus.py đã ingest xong 10 doc):
    python -m poc.kg_ontology.build_ontology_yaml
"""
from __future__ import annotations

import os
import re
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import yaml  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Document  # noqa: E402
from poc.kg_ontology import ground_truth_data as gt  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "ontology")


def normalize_name(name: str) -> str:
    """Khoá so khớp: gộp khoảng trắng + casefold — trùng logic với ontology/loader.py
    (không import từ đó: loader.py load YAML mà FILE NÀY chính là script SINH RA YAML đó)."""
    return re.sub(r"\s+", " ", name or "").strip().casefold()

ENTITY_TYPES = {
    "VanBan": {
        "description": "Một văn bản pháp lý/quyết định cụ thể (Nghị định, Thông tư, Quyết định nội bộ)",
        "attributes": ["so_hieu", "loai", "cap", "ngay_ban_hanh", "hieu_luc_tu", "trang_thai"],
    },
    "KhaiNiem": {
        "description": (
            "Khái niệm/chủ đề tuân thủ dùng chung xuyên nhiều văn bản "
            "(vd Mật khẩu, MFA, Dữ liệu cá nhân, KYC)"
        ),
    },
    "GiaTriQuyDinh": {
        "description": (
            "Một giá trị/ngưỡng/quy định CỤ THỂ mà 1 văn bản gán cho 1 khái niệm "
            "(vd '12 ký tự', '15 phút', '10 năm')"
        ),
    },
}

RELATION_TYPES = {
    "CAN_CU": {
        "description": "Văn bản A lấy văn bản B làm căn cứ pháp lý / tuân thủ theo B",
        "keywords": ["căn cứ", "tuân thủ", "phù hợp với", "complies", "based on", "dựa trên"],
    },
    "THAM_CHIEU": {
        "description": "Văn bản A dẫn chiếu tới văn bản B (không phải căn cứ pháp lý, không thay thế)",
        "keywords": ["tham chiếu", "dẫn chiếu", "reference", "refers to", "theo quy định tại"],
    },
    "THAY_THE": {
        "description": (
            "Văn bản A thay thế văn bản B — CÓ THỂ chỉ thay thế MỘT PHẦN "
            "(kiểm tra kỹ phần nào vẫn giữ hiệu lực)"
        ),
        "keywords": ["thay thế", "supersede", "replace", "hết hiệu lực thi hành"],
        "properties": ["partial", "giu_hieu_luc"],
    },
    "XUNG_DOT": {
        "description": (
            "Văn bản A và B quy định khác nhau cho CÙNG 1 khái niệm — có thể đã tuyên bố "
            "ưu tiên rõ ràng, có thể im lặng (cần cảnh báo), có thể là carve-out pháp luật "
            "chuyên ngành (KHÔNG phải xung đột thật, không báo động giả)"
        ),
        "keywords": ["xung đột", "mâu thuẫn", "conflict", "trái với", "khác với"],
        "properties": ["loai", "uu_tien_cho"],
    },
    "QUY_DINH": {
        "description": "Văn bản quy định 1 giá trị/ngưỡng cụ thể",
        "keywords": ["quy định", "yêu cầu", "phải có", "tối thiểu", "tối đa"],
    },
    "AP_DUNG_CHO": {
        "description": "1 giá trị/ngưỡng cụ thể áp dụng cho 1 khái niệm nào",
        "keywords": ["áp dụng cho", "applies to", "của", "đối với"],
    },
}

ALLOWED_TRIPLES = [
    ["VanBan", "CAN_CU", "VanBan"],
    ["VanBan", "THAM_CHIEU", "VanBan"],
    ["VanBan", "THAY_THE", "VanBan"],
    ["VanBan", "XUNG_DOT", "VanBan"],
    ["VanBan", "QUY_DINH", "GiaTriQuyDinh"],
    ["GiaTriQuyDinh", "AP_DUNG_CHO", "KhaiNiem"],
]


def _collect_catalog_names(tree_node_list: list[dict]) -> list[str]:
    """Duyệt toàn bộ node (mọi cấp, không chỉ leaf) trong 1 cây catalog, lấy hết 'name'."""
    names: list[str] = []
    for node in tree_node_list or []:
        name = node.get("name")
        if name:
            names.append(name)
        names.extend(_collect_catalog_names(node.get("children") or []))
    return names


def _load_catalogs_by_code() -> dict[str, list[str]]:
    """{doc_code: [tên node catalog, ...]} cho 10 document đã ingest (title == pdf_stem)."""
    stem_to_code = {d["pdf_stem"]: d["code"] for d in gt.DOCUMENTS}
    db = SessionLocal()
    try:
        rows = db.query(Document).filter(Document.category == "tuan_thu").all()
        by_code: dict[str, list[str]] = {}
        for row in rows:
            code = stem_to_code.get(row.title)
            if code is None:
                print(f"  !! Document title '{row.title}' không khớp pdf_stem nào trong ground_truth_data")
                continue
            by_code[code] = _collect_catalog_names((row.catalog or {}).get("tree", []))
        return by_code
    finally:
        db.close()


_PAREN_RE = __import__("re").compile(r"\s*\([^)]*\)\s*$")
_STOPWORDS = {"và", "của", "các", "cho", "theo", "khi", "là", "có", "được", "này", "về"}


def _significant_words(text: str) -> list[str]:
    """Bỏ hậu tố trong ngoặc đơn cuối câu (vd '(session timeout)', '(1-5)' — chú thích
    tiếng Anh tôi tự thêm, không chắc xuất hiện y hệt trong catalog tiếng Việt) rồi tách
    từ có nghĩa (>=3 ký tự, bỏ stopword). KHÔNG đụng dấu '/' (vd 'KYC / Nhận biết khách
    hàng') — giữ nguyên cả 2 vế, vế tiếng Việt vẫn cần để so khớp."""
    stripped = _PAREN_RE.sub("", text)
    words = normalize_name(stripped).split()
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _cross_check_concepts(catalogs_by_code: dict[str, list[str]]) -> list[dict]:
    """Với mỗi concept ở GROUND_TRUTH §3: gộp toàn bộ tên node catalog của đúng những
    doc nó khai "xuất hiện tại" thành 1 blob, rồi coi là match nếu >=60% từ có nghĩa của
    tên concept (đã bỏ chú thích ngoặc) xuất hiện đâu đó trong blob. Heuristic — không
    phải NLP thật, chỉ để khoanh vùng cần soát tay, KHÔNG tự động quyết định thay người."""
    enriched = []
    for concept in gt.CONCEPTS:
        words = _significant_words(concept["name"])
        seen_in = []
        for code in concept["xuat_hien_tai"]:
            blob = normalize_name(" | ".join(catalogs_by_code.get(code, [])))
            hits = [w for w in words if w in blob]
            if words and len(hits) / len(words) >= 0.6:
                seen_in.append({"doc": code, "matched_words": hits})
        enriched.append({**concept, "catalog_seen_in": seen_in})
        if not seen_in:
            print(f"  !! Concept '{concept['name']}' KHÔNG match node catalog nào ở {concept['xuat_hien_tai']}")
    return enriched


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Đọc catalog 10 document (category=tuan_thu) từ SQLite...")
    catalogs_by_code = _load_catalogs_by_code()
    print(f"  -> đọc được catalog cho {len(catalogs_by_code)}/10 document")

    print("Đối chiếu 18 concept (GROUND_TRUTH §3) với node catalog...")
    concepts_enriched = _cross_check_concepts(catalogs_by_code)
    matched = sum(1 for c in concepts_enriched if c["catalog_seen_in"])
    print(f"  -> {matched}/{len(concepts_enriched)} concept match được >=1 node catalog")

    entities_yaml = {
        "entity_types": ENTITY_TYPES,
        "known_entities": {
            "documents": gt.DOCUMENTS,
            "concepts": concepts_enriched,
        },
    }
    relations_yaml = {
        "relation_types": RELATION_TYPES,
        "allowed_triples": ALLOWED_TRIPLES,
        "known_relations": gt.RELATIONS,
    }

    entities_path = os.path.join(OUT_DIR, "entities.yaml")
    relations_path = os.path.join(OUT_DIR, "relations.yaml")
    with open(entities_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(entities_yaml, f, allow_unicode=True, sort_keys=False, width=100)
    with open(relations_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(relations_yaml, f, allow_unicode=True, sort_keys=False, width=100)

    print(f"\nĐã ghi {entities_path}")
    print(f"Đã ghi {relations_path}")
    print("\n=> Soát tay các dòng '!!' ở trên trước khi dùng ontology này để build KG.")


if __name__ == "__main__":
    main()
