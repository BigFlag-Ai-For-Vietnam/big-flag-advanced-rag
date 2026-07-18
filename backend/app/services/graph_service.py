"""Choke point cho MỌI đọc Neo4j lúc QUERY-TIME — nhẹ (chỉ cần driver `neo4j`), an toàn để
chạy trong CẢ 2 image (`backend` và `retrieval-mcp`). Build graph (LightRAG, nặng) sống
riêng ở `app/services/kg/`, chỉ được gọi từ `pipeline.py` — xem invariant "Graph boundary"
trong CLAUDE.md. Không import gì từ `app.services.kg.*` ở đây.

Mọi lỗi Neo4j (chưa deploy, mất kết nối, ...) đều bị nuốt và trả về rỗng/deep-degrade —
graph là baseline BỔ SUNG cho chunk-based RAG, không được phép làm sập luồng query chính.

Shape 1 "graph fact" (dùng chung engine.py/nodes.py/playground.py):
{
    "fact_id": str,              # f"{source}|{relation}|{target}" — key dedup
    "source_entity": str, "source_type": str,      # VanBan|KhaiNiem|GiaTriQuyDinh
    "relation": str,             # CAN_CU|THAY_THE|THAM_CHIEU|UU_TIEN_HON|QUY_DINH|AP_DUNG_CHO
    "target_entity": str, "target_type": str,
    "properties": dict,          # vd {"partial": True, "giu_hieu_luc": "..."} hoặc {}
    "source_document_title": str, "description": str,
    "strategy": str,             # "citation_neighbor" | "concept_traversal"
    "score": float,
}
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache

from neo4j import Driver, GraphDatabase

from app.config import settings
from app.services import embedding_service

logger = logging.getLogger("graph_service")

# 4 loại quan hệ document-to-document (citation_extractor.py) — xem docstring module đó.
_CITATION_RELS = ["CAN_CU", "THAY_THE", "THAM_CHIEU", "UU_TIEN_HON"]

# len>=2 (không len>=3): giữ được từ tiếng Việt 2 ký tự có nghĩa (vd "độ" trong "Cấp Độ 4").
_STOPWORDS = {
    "và", "của", "các", "cho", "theo", "khi", "là", "có", "được", "này", "về", "một",
    "tại", "để", "do", "từ", "với", "hay", "nếu", "sẽ", "đã", "đang", "sau", "trước",
    "trên", "trong", "ngoài", "mà", "thì", "nên", "còn", "cả", "mọi", "những", "nào",
}


def is_configured() -> bool:
    return bool(settings.neo4j_uri and settings.neo4j_username and settings.neo4j_password)


@lru_cache
def _driver() -> Driver:
    return GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))


def close_driver() -> None:
    """Gọi từ main.py _shutdown — đóng driver nếu đã từng mở."""
    if _driver.cache_info().currsize:
        _driver().close()
    _driver.cache_clear()


def _fact_id(source: str, relation: str, target: str) -> str:
    return f"{source}|{relation}|{target}"


def _clean_props(props: dict | None) -> dict:
    return {k: v for k, v in (props or {}).items() if k not in ("ontology_relation", "description")}


def _row_to_fact(row: dict, strategy: str, score: float) -> dict:
    rel_props = row.get("rel_props") or {}
    return {
        "fact_id": _fact_id(row["source"], row["relation"], row["target"]),
        "source_entity": row["source"],
        "source_type": row.get("source_type") or "",
        "relation": row["relation"],
        "target_entity": row["target"],
        "target_type": row.get("target_type") or "",
        "properties": _clean_props(rel_props),
        "source_document_title": row.get("file_path") or "",
        "description": rel_props.get("description") or "",
        "strategy": strategy,
        "score": score,
    }


def citation_neighbors(document_titles: list[str], max_hops: int = 1) -> list[dict]:
    """Quan hệ văn bản-văn bản (CAN_CU/THAY_THE/THAM_CHIEU/UU_TIEN_HON) quanh các VanBan có
    `file_path` (= Document.title) khớp `document_titles` — vd văn bản vừa xuất hiện trong
    chunk hits, xem quan hệ CĂN_CỨ/THAY_THẾ của nó với văn bản khác."""
    if not document_titles or not is_configured():
        return []
    hops = max(1, int(max_hops))
    query = f"""
        MATCH (v {{entity_type: 'VanBan'}}) WHERE v.file_path IN $titles
        MATCH path = (v)-[rels:DIRECTED*1..{hops}]-(n)
        WHERE ALL(r IN rels WHERE r.ontology_relation IN $rels_allowed)
        UNWIND rels AS r
        WITH DISTINCT startNode(r) AS s, endNode(r) AS t, r
        RETURN s.entity_id as source, s.entity_type as source_type, t.entity_id as target,
               t.entity_type as target_type, r.ontology_relation as relation,
               properties(r) as rel_props, s.file_path as file_path
        LIMIT 100
    """
    try:
        with _driver().session() as session:
            rows = session.run(query, titles=document_titles, rels_allowed=_CITATION_RELS).data()
        return [_row_to_fact(row, "citation_neighbor", 1.0) for row in rows]
    except Exception as exc:  # noqa: BLE001 — Neo4j down/lỗi không được chặn query chính
        logger.warning("[citation_neighbors] lỗi (Neo4j chưa sẵn sàng?): %s", exc)
        return []


def _normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()


def _significant_words(text: str) -> set[str]:
    return {w for w in _normalize_name(text).split() if len(w) >= 2 and w not in _STOPWORDS}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)


def _match_concept_names(query_text: str, concepts: list[dict], top_k: int) -> list[str]:
    """Substring/word-overlap trước (rẻ, chính xác cao); embedding cosine fallback nếu
    không match từ nào — threshold đã calibrate thật ở PoC (model embedding tiếng Việt
    cho similarity thấp hơn trực giác, KHÔNG dùng 0.8 mặc định)."""
    q_words = _significant_words(query_text)
    scored: list[tuple[float, str]] = []
    if q_words:
        for c in concepts:
            c_words = _significant_words(c["name"])
            if not c_words:
                continue
            overlap = len(q_words & c_words)
            if overlap and overlap / len(c_words) >= 0.5:
                scored.append((overlap / len(c_words), c["name"]))
    if scored:
        scored.sort(reverse=True)
        return [name for _, name in scored[:top_k]]

    try:
        query_vec = embedding_service.embed_query(query_text)
        texts = [f"{c['name']}. {c['desc']}".strip(". ") for c in concepts]
        concept_vecs = embedding_service.embed_texts(texts)
    except Exception as exc:  # noqa: BLE001 — embedding lỗi -> bỏ qua fallback, không crash
        logger.warning("[concept_matches] embedding fallback lỗi: %s", exc)
        return []
    threshold = settings.retrieval_graph_concept_embedding_threshold
    sims = [(_cosine(query_vec, v), c["name"]) for v, c in zip(concept_vecs, concepts)]
    sims.sort(reverse=True)
    return [name for sim, name in sims[:top_k] if sim >= threshold]


def concept_matches(query_text: str, top_k: int = 5) -> list[dict]:
    """Bundle giá trị (GiaTriQuyDinh) + văn bản nguồn theo khái niệm (KhaiNiem) khớp
    `query_text` — traverse KhaiNiem <-AP_DUNG_CHO- GiaTriQuyDinh <-QUY_DINH- VanBan, để lộ
    RA đủ các giá trị khác nhau (có thể mâu thuẫn) cho cùng 1 khái niệm, kèm nguồn — LLM tự
    reasoning xung đột/thay thế ở query time, KHÔNG vật hoá quan hệ XUNG_ĐỘT ở đây."""
    if not query_text or not is_configured():
        return []
    try:
        with _driver().session() as session:
            concepts = session.run(
                "MATCH (n {entity_type: 'KhaiNiem'}) "
                "RETURN n.entity_id as name, coalesce(n.description,'') as desc"
            ).data()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[concept_matches] lỗi lấy KhaiNiem (Neo4j chưa sẵn sàng?): %s", exc)
        return []
    if not concepts:
        return []

    matched = _match_concept_names(query_text, concepts, top_k)
    if not matched:
        return []

    try:
        with _driver().session() as session:
            rows = session.run(
                """
                MATCH (c {entity_type:'KhaiNiem'}) WHERE c.entity_id IN $names
                OPTIONAL MATCH (val)-[r_ap]->(c) WHERE r_ap.ontology_relation = 'AP_DUNG_CHO'
                OPTIONAL MATCH (van {entity_type:'VanBan'})-[r_qd]->(val)
                    WHERE r_qd.ontology_relation = 'QUY_DINH'
                RETURN c.entity_id as concept, val.entity_id as value, val.entity_type as value_type,
                       properties(r_ap) as ap_props, van.entity_id as vanban, val.file_path as file_path,
                       properties(r_qd) as qd_props
                LIMIT 200
                """,
                names=matched,
            ).data()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[concept_matches] lỗi traverse (Neo4j chưa sẵn sàng?): %s", exc)
        return []

    facts: list[dict] = []
    for row in rows:
        if not row.get("value"):
            continue
        ap_props = row.get("ap_props") or {}
        facts.append({
            "fact_id": _fact_id(row["value"], "AP_DUNG_CHO", row["concept"]),
            "source_entity": row["value"], "source_type": row.get("value_type") or "",
            "relation": "AP_DUNG_CHO", "target_entity": row["concept"], "target_type": "KhaiNiem",
            "properties": _clean_props(ap_props), "source_document_title": row.get("file_path") or "",
            "description": ap_props.get("description") or "",
            "strategy": "concept_traversal", "score": 1.0,
        })
        if row.get("vanban"):
            qd_props = row.get("qd_props") or {}
            facts.append({
                "fact_id": _fact_id(row["vanban"], "QUY_DINH", row["value"]),
                "source_entity": row["vanban"], "source_type": "VanBan",
                "relation": "QUY_DINH", "target_entity": row["value"], "target_type": row.get("value_type") or "",
                "properties": _clean_props(qd_props), "source_document_title": row.get("file_path") or "",
                "description": qd_props.get("description") or "",
                "strategy": "concept_traversal", "score": 1.0,
            })
    return facts


def delete_by_document(document_id: str, document_title: str) -> None:
    """Xoá node graph của 1 document — ưu tiên `document_id` (đã stamp lúc build); fallback
    `file_path == title AND document_id IS NULL` cho data cũ chưa được stamp. Document.title
    KHÔNG unique nên chỉ xoá theo title khi node chưa có document_id (tránh xoá nhầm document
    khác cùng tên đã stamp)."""
    if not is_configured():
        return
    try:
        with _driver().session() as session:
            session.run("MATCH (n) WHERE n.document_id = $did DETACH DELETE n", did=document_id)
            session.run(
                "MATCH (n) WHERE n.file_path = $title AND n.document_id IS NULL DETACH DELETE n",
                title=document_title,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[delete_by_document] lỗi (Neo4j chưa sẵn sàng?): %s", exc)


def stats() -> dict:
    """Health check — node/edge count theo type, dùng lúc rollout để xác nhận graph không
    rỗng trước khi bật `RETRIEVAL_ENABLE_GRAPH`."""
    if not is_configured():
        return {"configured": False}
    try:
        with _driver().session() as session:
            node_rows = session.run(
                "MATCH (n) WHERE n.entity_type IS NOT NULL RETURN n.entity_type as type, count(*) as n"
            ).data()
            edge_rows = session.run(
                "MATCH ()-[r]->() WHERE r.ontology_relation IS NOT NULL "
                "RETURN r.ontology_relation as type, count(*) as n"
            ).data()
        return {
            "configured": True,
            "nodes_by_type": {row["type"]: row["n"] for row in node_rows},
            "edges_by_type": {row["type"]: row["n"] for row in edge_rows},
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("[stats] lỗi (Neo4j chưa sẵn sàng?): %s", exc)
        return {"configured": True, "error": str(exc)}
