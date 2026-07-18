"""Deterministic citation-edge extractor — KHÔNG dùng LLM.

Ý tưởng: CĂN_CỨ/THAM_CHIẾU/THAY_THẾ/ƯU_TIÊN_HƠN là quan hệ document-to-document được VIẾT
RA tường minh trong văn bản, luôn kèm số hiệu định danh (vd "09/2024/TT-NHNN") — một
citation ID cực mạnh, không cần LLM đoán, regex + verb context là đủ, chính xác hơn hẳn
LightRAG's free-form extraction cho ĐÚNG loại quan hệ này (LightRAG generic tốt cho
KhaiNiem/GiaTriQuyDinh nhưng không đáng tin cho văn bản-văn bản).

Chạy per-document (`run_for_document`), ngay sau `entity_resolution.resolve_vanban()` +
stamp `document_id` (build_service.py) — PHẢI chạy SAU resolve_vanban(), nếu không mỗi
biến thể tên VanBan sẽ tạo edge riêng, không hội tụ về 1 node. Tìm node "tự-tham-chiếu"
của document (VanBan mà chính document đó tự nhắc số hiệu của mình) qua `file_path ==
document_title` — LightRAG stamp field này cho MỌI entity trích từ `ainsert(...,
file_paths=title)` — không cần bảng tra cứu ngoài (khác bản PoC ban đầu dùng
ground_truth_data.py, chỉ có ở 10 tài liệu compliance mẫu, không tồn tại ở production).

Giới hạn đã biết: chỉ bắt số hiệu dạng \\d+/\\d{4}/(NĐ-CP|TT-NHNN|QĐ-DDB) — KHÔNG bắt
tham chiếu tới "Luật ABC năm XXXX" (không có số hiệu chuẩn) — case này vẫn cần
LightRAG/LLM tự do trích.
"""
from __future__ import annotations

import re

from neo4j import Driver

from app.services.kg.so_hieu import SO_HIEU_RE

_CONTEXT_BEFORE = 150  # đủ dài cho câu kiểu "áp dụng thay cho thời hạn X ... (số hiệu)"
_CONTEXT_AFTER = 300   # _classify_bidirectional luôn chọn verb GẦN citation nhất nên
                       # nới rộng window không tăng false-positive, chỉ tăng candidate

# Verb có thể nằm TRƯỚC hay SAU citation tuỳ câu:
#   "...(Quyết định số 342...) thì ưu tiên áp dụng..."     -> verb SAU
#   "...theo Quy chế An toàn thông tin hiện hành (QĐ 342)"  -> cụm "hiện hành" SAU citation
#   "...áp dụng thay cho thời hạn 05 năm ... (QĐ 455)..."   -> verb TRƯỚC, xa citation
# => phải quét CẢ 2 phía (_classify_bidirectional), không chỉ before.
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
    tuyệt đối (không chỉ before)."""
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
    """Pure function (regex, zero I/O) — an toàn để unit-test trực tiếp."""
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


def _find_by_so_hieu(session, so_hieu: str) -> str | None:
    rec = session.run(
        "MATCH (n {entity_type: 'VanBan'}) WHERE n.entity_id CONTAINS $so_hieu "
        "RETURN n.entity_id as name LIMIT 1",
        so_hieu=so_hieu,
    ).single()
    return rec["name"] if rec else None


def _find_self_vanban(session, document_title: str) -> str | None:
    """VanBan node mà CHÍNH document tự nhắc số hiệu của mình — nhận diện qua `file_path`
    (LightRAG stamp = Document.title cho MỌI entity trích từ document này)."""
    rec = session.run(
        "MATCH (n {entity_type: 'VanBan'}) WHERE n.file_path = $title "
        "RETURN n.entity_id as name LIMIT 1",
        title=document_title,
    ).single()
    return rec["name"] if rec else None


def _ensure_node(session, so_hieu: str) -> str:
    """Tìm node VanBan đã có (sau resolve_vanban) chứa đúng số hiệu; nếu chưa có (external
    reference, tài liệu này chưa từng được ingest/LightRAG chưa từng extract) thì tạo node
    tối giản mới, entity_id = chính số hiệu (không đoán tên đầy đủ)."""
    existing = _find_by_so_hieu(session, so_hieu)
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
    # (không phải CREATE mới) -> classification của citation_extractor bị lặng lẽ bỏ qua.
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
    # này — nếu LightRAG đã tự trích 1 edge KHÁC LOẠI (trong 4 loại này) cho cùng cặp
    # (s,t)/(t,s), xoá để không tồn tại song song 2 phân loại mâu thuẫn cho cùng 1 cặp văn bản.
    session.run(
        """
        MATCH (s {entity_id: $source_id})-[r]-(t {entity_id: $target_id})
        WHERE r.ontology_relation IN $citation_types AND r.ontology_relation <> $rel_type
        DELETE r
        """,
        source_id=source_id, target_id=target_id, rel_type=rel_type,
        citation_types=_CITATION_TYPES,
    )


def run_for_document(driver: Driver, document_title: str, full_text: str) -> dict:
    """Trích + ghi citation edge cho 1 document (build_service gọi ngay sau resolve_vanban()
    của chính document đó). Không cần ground truth/SQLite — chỉ cần full_text + title."""
    stats = {"citations_found": 0, "edges_written": 0, "by_type": {}}
    citations = extract_citations_from_text(full_text)
    if not citations:
        return stats

    with driver.session() as session:
        source_id = _find_self_vanban(session, document_title)
        if source_id is None:
            return stats  # document chưa có VanBan tự-tham-chiếu nào được extract — bỏ qua

        for c in citations:
            if c["target_so_hieu"] in source_id:
                continue  # tự trích chính mình (số hiệu lặp lại trong header) — bỏ
            target_id = _ensure_node(session, c["target_so_hieu"])
            write_citation_edge(session, source_id, target_id, c)
            stats["citations_found"] += 1
            stats["edges_written"] += 1
            stats["by_type"][c["type"]] = stats["by_type"].get(c["type"], 0) + 1
    return stats
