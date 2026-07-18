"""Deterministic citation-edge extractor — KHÔNG dùng LLM.

Ý tưởng (đúng insight đã bàn): CĂN_CỨ/THAM_CHIẾU/THAY_THẾ/ƯU_TIÊN_HƠN là quan hệ
document-to-document được VIẾT RA tường minh trong văn bản, luôn kèm số hiệu định danh
(vd "09/2024/TT-NHNN") — một citation ID cực mạnh, không cần LLM đoán, regex + verb
context là đủ, chính xác hơn hẳn LightRAG's free-form extraction cho ĐÚNG loại quan hệ
này (LightRAG generic tốt cho KhaiNiem/GiaTriQuyDinh nhưng không có edge nào giữa văn bản
với văn bản đáng tin cậy, đã thấy rõ qua nhiều lần chạy — Q6 gãy, THAY_THE có nhưng
không có property partial/giữ_hiệu_lực).

Đây là bước BỔ SUNG (ghi thẳng edge vào Neo4j, MERGE vào đúng VanBan node đã canonical
hoá bởi entity_resolution.resolve_vanban() — PHẢI chạy resolve_vanban() TRƯỚC khi chạy
file này, nếu không mỗi biến thể tên sẽ tạo edge riêng, không hội tụ về 1 node).

Giới hạn đã biết: chỉ bắt số hiệu dạng \\d+/\\d{4}/(NĐ-CP|TT-NHNN|QĐ-DDB) — KHÔNG bắt
tham chiếu tới "Luật ABC năm XXXX" (không có số hiệu chuẩn, vd "Luật Phòng chống rửa
tiền 2022") — case này vẫn cần LightRAG/LLM tự do trích (hoặc thêm regex riêng nếu cần).
"""
from __future__ import annotations

import os
import re
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from neo4j import Driver  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Chunk, Document  # noqa: E402
from poc.kg_ontology import ground_truth_data as gt  # noqa: E402
from poc.kg_ontology.entity_resolution import SO_HIEU_RE, _driver  # noqa: E402

_CONTEXT_BEFORE = 150  # đủ dài cho câu kiểu "áp dụng thay cho thời hạn X ... (số hiệu)"
_CONTEXT_AFTER = 300   # _classify_bidirectional luôn chọn verb GẦN citation nhất nên
                       # nới rộng window không tăng false-positive, chỉ tăng candidate

# Học từ đọc THẲNG docs_content.py (nguồn sinh PDF) cho cả 3 cạnh THAM_CHIẾU/ưu tiên của
# ground truth — verb có thể nằm TRƯỚC hay SAU citation tuỳ câu:
#   "...(Quyết định số 342...) thì ưu tiên áp dụng..."     -> verb SAU
#   "...theo Quy chế An toàn thông tin hiện hành (QĐ 342)"  -> cụm "hiện hành" SAU citation
#   "...áp dụng thay cho thời hạn 05 năm ... (QĐ 455)..."   -> verb TRƯỚC, xa citation
# => phải quét CẢ 2 phía (_classify_bidirectional), không chỉ before như bản đầu.
_VERB_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"thay\s+thế", re.IGNORECASE), "THAY_THE"),
    (re.compile(r"ưu\s+tiên", re.IGNORECASE), "UU_TIEN_HON"),
    (re.compile(r"áp\s+dụng\s+thay\s+cho|(?<!thay\s)\bthay\s+cho\b", re.IGNORECASE), "THAM_CHIEU"),
    (re.compile(r"tham\s+chiếu|dẫn\s+chiếu|hiện\s+hành", re.IGNORECASE), "THAM_CHIEU"),
    (re.compile(r"theo\s+Điều\s+\d+|căn\s+cứ|tuân\s+thủ|phù\s+hợp\s+với|theo\s+quy\s+định\s+tại", re.IGNORECASE), "CAN_CU"),
]

_PARTIAL_RE = re.compile(r"một\s+phần|riêng|tiếp\s+tục\s+có\s+hiệu\s+lực|giữ\s+hiệu\s+lực", re.IGNORECASE)
_RETAINED_SCOPE_RE = re.compile(r"Phụ\s+lục\s+\d+[^.;\n]{0,80}", re.IGNORECASE)


def _classify_bidirectional(before: str, after: str) -> str | None:
    """Quét verb CẢ 2 phía quanh citation, chọn verb GẦN citation nhất theo khoảng cách
    tuyệt đối (không chỉ before như bản đầu) — xem lý do ở comment _VERB_PATTERNS."""
    best_type, best_dist = None, None
    for pat, name in _VERB_PATTERNS:
        for m in pat.finditer(before):
            dist = len(before) - m.end()  # càng nhỏ càng gần citation (đứng ngay trước)
            if best_dist is None or dist < best_dist:
                best_dist, best_type = dist, name
        for m in pat.finditer(after):
            dist = m.start()  # càng nhỏ càng gần citation (đứng ngay sau)
            if best_dist is None or dist < best_dist:
                best_dist, best_type = dist, name
    return best_type


def extract_citations_from_text(doc_text: str) -> list[dict]:
    results = []
    for m in SO_HIEU_RE.finditer(doc_text):
        so_hieu = m.group(0)
        before = doc_text[max(0, m.start() - _CONTEXT_BEFORE) : m.start()]
        after = doc_text[m.end() : m.end() + _CONTEXT_AFTER]

        rel_type = _classify_bidirectional(before, after)
        if rel_type is None:
            continue

        partial = False
        giu_hieu_luc = None
        if rel_type == "THAY_THE" and _PARTIAL_RE.search(after):
            partial = True
            scope_m = _RETAINED_SCOPE_RE.search(after)
            giu_hieu_luc = scope_m.group(0).strip() if scope_m else None

        results.append({
            "target_so_hieu": so_hieu,
            "type": rel_type,
            "partial": partial,
            "giu_hieu_luc": giu_hieu_luc,
            "evidence": f"...{before.strip()[-60:]} [{so_hieu}] {after.strip()[:80]}...",
        })
    return results


def _load_document_texts() -> list[tuple[str, str]]:
    """[(so_hieu nguồn, full_text), ...] cho 10 document đã ingest."""
    stem_to_so_hieu = {d["pdf_stem"]: d["so_hieu"] for d in gt.DOCUMENTS}
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.category == "tuan_thu").all()
        out = []
        for doc in docs:
            so_hieu = stem_to_so_hieu.get(doc.title)
            if not so_hieu:
                continue
            chunks = (
                db.query(Chunk)
                .filter(Chunk.document_id == doc.id)
                .order_by(Chunk.chunk_index)
                .all()
            )
            full_text = "\n\n".join(c.raw_text for c in chunks)
            out.append((so_hieu, full_text))
        return out
    finally:
        db.close()


def _find_canonical_node(session, so_hieu: str) -> str | None:
    rec = session.run(
        "MATCH (n {entity_type: 'VanBan'}) WHERE n.entity_id CONTAINS $so_hieu "
        "RETURN n.entity_id as name LIMIT 1",
        so_hieu=so_hieu,
    ).single()
    return rec["name"] if rec else None


def _ensure_node(session, so_hieu: str) -> str:
    """Tìm node VanBan đã có (sau resolve_vanban) chứa đúng số hiệu; nếu chưa có (external
    reference, vd TT18/2018 chưa từng được LightRAG extract) thì tạo node tối giản mới,
    entity_id = chính số hiệu (không đoán tên đầy đủ)."""
    existing = _find_canonical_node(session, so_hieu)
    if existing:
        return existing
    session.run(
        "MERGE (n {entity_id: $so_hieu}) "
        "ON CREATE SET n.entity_type = 'VanBan', "
        "n.description = 'Văn bản tham chiếu (external, tạo bởi citation_extractor)', "
        "n.extraction_method = 'citation_extractor'",
        so_hieu=so_hieu,
    )
    return so_hieu


# 4 type citation_extractor tự trích — dùng để biết cạnh nào "thuộc quyền" của mình,
# tránh xung khắc với type khác LightRAG tự trích cho CÙNG 1 cặp node (xem write_citation_edge).
_CITATION_TYPES = ["CAN_CU", "THAY_THE", "THAM_CHIEU", "UU_TIEN_HON"]


def write_citation_edge(session, source_id: str, target_id: str, citation: dict) -> None:
    rel_type = citation["type"]
    # MERGE có ontology_relation NGAY TRONG pattern — nếu chỉ MERGE (s)-[:DIRECTED]->(t)
    # (không kèm property trong pattern) thì lúc LightRAG đã tự trích SẴN 1 edge khác loại
    # cho đúng cặp (s,t) này, MERGE sẽ khớp nhầm vào edge đó và ON CREATE SET không chạy
    # (không phải CREATE mới) -> classification của citation_extractor bị lặng lẽ bỏ qua
    # (đã bắt gặp thật: cặp QĐ401-QĐ342, UU_TIEN_HON của mình bị nuốt bởi THAM_CHIEU cũ
    # của LightRAG). Kèm property trong pattern để LUÔN tạo/tìm đúng edge CỦA MÌNH.
    session.run(
        """
        MATCH (s {entity_id: $source_id}), (t {entity_id: $target_id})
        MERGE (s)-[r:DIRECTED {ontology_relation: $rel_type}]->(t)
        ON CREATE SET
            r.partial = $partial,
            r.giu_hieu_luc = $giu_hieu_luc,
            r.evidence = $evidence,
            r.extraction_method = 'citation_extractor',
            r.description = $evidence
        """,
        source_id=source_id, target_id=target_id, rel_type=rel_type,
        partial=citation["partial"], giu_hieu_luc=citation["giu_hieu_luc"] or "",
        evidence=citation["evidence"],
    )
    # citation_extractor đáng tin hơn LightRAG cho ĐÚNG 4 loại quan hệ document-to-document
    # này (đã verify: bắt được ngoại lệ Phụ lục 02 mà LightRAG 3 lần chạy đều bỏ lỡ) — nếu
    # LightRAG đã tự trích 1 edge KHÁC LOẠI (trong 4 loại này) cho cùng cặp (s,t)/(t,s), xoá
    # để không tồn tại song song 2 phân loại mâu thuẫn cho cùng 1 cặp văn bản.
    session.run(
        """
        MATCH (s {entity_id: $source_id})-[r]-(t {entity_id: $target_id})
        WHERE r.ontology_relation IN $citation_types AND r.ontology_relation <> $rel_type
        DELETE r
        """,
        source_id=source_id, target_id=target_id, rel_type=rel_type,
        citation_types=_CITATION_TYPES,
    )


def run(driver: Driver) -> dict:
    stats = {"scanned_docs": 0, "citations_found": 0, "edges_written": 0, "by_type": {}}
    doc_texts = _load_document_texts()
    with driver.session() as session:
        for source_so_hieu, full_text in doc_texts:
            stats["scanned_docs"] += 1
            source_id = _find_canonical_node(session, source_so_hieu)
            if source_id is None:
                print(f"  !! Không tìm thấy VanBan node cho nguồn '{source_so_hieu}' — bỏ qua")
                continue

            citations = extract_citations_from_text(full_text)
            for c in citations:
                if c["target_so_hieu"] == source_so_hieu:
                    continue  # tự trích chính mình (vd số hiệu lặp lại trong header) — bỏ
                stats["citations_found"] += 1
                target_id = _ensure_node(session, c["target_so_hieu"])
                write_citation_edge(session, source_id, target_id, c)
                stats["edges_written"] += 1
                stats["by_type"][c["type"]] = stats["by_type"].get(c["type"], 0) + 1
                print(
                    f"  [{source_so_hieu}] -{c['type']}"
                    f"{' (partial)' if c['partial'] else ''}-> [{c['target_so_hieu']}]"
                    + (f"  giữ_hiệu_lực={c['giu_hieu_luc']!r}" if c["giu_hieu_luc"] else "")
                )
    return stats


def main() -> None:
    driver = _driver()
    try:
        print("=== Citation extractor (deterministic, regex + verb context) ===")
        stats = run(driver)
        print(f"\nQuét {stats['scanned_docs']} document, tìm {stats['citations_found']} citation, "
              f"ghi {stats['edges_written']} edge.")
        print("Theo loại:", stats["by_type"])
    finally:
        driver.close()


if __name__ == "__main__":
    main()
