"""Vá lỗ hổng phát hiện được: 56/67 (84%) node GiaTriQuyDinh KHÔNG có lấy 1 cạnh nào —
không nối được về văn bản nguồn, càng không nối được về KhaiNiem chung. Không phải do
thiếu ontology cho XUNG_ĐỘT (đúng như đã thống nhất, KHÔNG nên vật hoá XUNG_ĐỘT) — mà vì
`classify_relation_keyword()` reject quá nhiều QUY_DINH/AP_DUNG_CHO hợp lệ, để lại value
node mồ côi mà agent không có đường traverse tới.

2 bước link, cả 2 đều KHÔNG cần LLM (dùng metadata có sẵn + embedding đã tính từ trước):

1. link_provenance() — VanBan -> GiaTriQuyDinh (QUY_DINH), dùng `file_path` LightRAG tự
   gán (= Document.title, truyền qua `ainsert(..., file_paths=doc.title)` lúc build KG) —
   khớp thẳng với VanBan canonical qua số hiệu, KHÔNG cần suy luận gì — deterministic
   100%, fix được ngay phần lớn node mồ côi.

2. link_concepts() — GiaTriQuyDinh -> KhaiNiem (AP_DUNG_CHO): substring/từ chung trước
   (rẻ, chính xác cao khi tên value chứa tên concept, vd "08 ký tự mật khẩu" chứa "mật
   khẩu"), embedding cosine similarity làm fallback cho phần còn lại.

Kết quả: từ KhaiNiem "Mật khẩu" giờ traverse được tới MỌI giá trị (08/12 ký tự) VÀ văn bản
nguồn của từng giá trị — đúng ý "lôi văn bản đó related vào entity Mật khẩu" — KHÔNG có
edge XUNG_ĐỘT nào bị tạo, để nguyên cho ReAct agent tự reasoning lúc query.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import numpy as np  # noqa: E402
from neo4j import Driver  # noqa: E402

from poc.kg_ontology import ground_truth_data as gt  # noqa: E402
from poc.kg_ontology.entity_resolution import SO_HIEU_RE, _driver  # noqa: E402
from poc.kg_ontology.llm_adapter import _embed  # noqa: E402
from poc.kg_ontology.ontology.loader import normalize_name  # noqa: E402

_STEM_TO_SO_HIEU = {d["pdf_stem"]: d["so_hieu"] for d in gt.DOCUMENTS}

# len>=3 (kiểu filter tiếng Anh) loại mất từ tiếng Việt 2 ký tự CÓ nghĩa (vd "độ" trong
# "Cấp Độ 4" — khớp "Phân loại cấp độ hệ thống"): hạ xuống len>=2, bù lại bằng liệt kê rõ
# stopword 2-3 ký tự KHÔNG mang nghĩa phân loại (hư từ/giới từ), thay vì cutoff độ dài.
_STOPWORDS = {
    "và", "của", "các", "cho", "theo", "khi", "là", "có", "được", "này", "về", "một",
    "tại", "để", "do", "từ", "với", "hay", "nếu", "sẽ", "đã", "đang", "sau", "trước",
    "trên", "trong", "ngoài", "mà", "thì", "nên", "còn", "cả", "mọi", "những", "nào",
}


def _significant_words(text: str) -> set[str]:
    return {w for w in normalize_name(text).split() if len(w) >= 2 and w not in _STOPWORDS}


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ------------------------------------------------------------------ 1. Provenance (VanBan -> value)

def link_provenance(driver: Driver) -> dict:
    stats = {"checked": 0, "linked": 0, "no_canonical_vanban": 0}
    with driver.session() as session:
        rows = session.run(
            "MATCH (n) WHERE n.entity_type IN ['GiaTriQuyDinh', 'KhaiNiem'] "
            "RETURN n.entity_id as name, n.file_path as file_path"
        ).data()
        for row in rows:
            stats["checked"] += 1
            so_hieu = _STEM_TO_SO_HIEU.get(row["file_path"])
            if not so_hieu:
                continue
            rec = session.run(
                "MATCH (v {entity_type:'VanBan'}) WHERE v.entity_id CONTAINS $so_hieu "
                "RETURN v.entity_id as name LIMIT 1",
                so_hieu=so_hieu,
            ).single()
            if rec is None:
                stats["no_canonical_vanban"] += 1
                continue
            session.run(
                """
                MATCH (v {entity_id: $vanban}), (n {entity_id: $node})
                MERGE (v)-[r:DIRECTED]->(n)
                ON CREATE SET r.ontology_relation = 'QUY_DINH', r.source = 'concept_linker.provenance'
                """,
                vanban=rec["name"], node=row["name"],
            )
            stats["linked"] += 1
    return stats


# ------------------------------------------------------------------ 2. Concept (value -> KhaiNiem)

def _substring_match(name: str, concept_names: list[str]) -> str | None:
    words = _significant_words(name)
    if not words:
        return None
    best, best_overlap = None, 0
    for cname in concept_names:
        cwords = _significant_words(cname)
        if not cwords:
            continue
        overlap = len(words & cwords)
        if overlap > best_overlap and overlap / len(cwords) >= 0.5:
            best, best_overlap = cname, overlap
    return best


def _embed_text(name: str, description: str) -> str:
    """Ghép tên + description để embed — bare NAME của 1 giá trị (vd "5 năm", "Cấp Độ 4")
    gần như vô nghĩa đứng 1 mình (áp dụng cho rất nhiều concept khác nhau); description
    ("Thời gian tối đa... lưu trữ dữ liệu cá nhân...") mới mang tín hiệu ngữ nghĩa mạnh để
    so khớp đúng concept — đây là fix chính cho phần lớn trong 43 giá trị chưa nối được."""
    desc = (description or "").strip()
    return f"{name}. {desc}" if desc else name


async def link_concepts(driver: Driver, embedding_threshold: float = 0.80) -> dict:
    with driver.session() as session:
        concepts = session.run(
            "MATCH (n {entity_type:'KhaiNiem'}) RETURN n.entity_id as name, coalesce(n.description,'') as desc"
        ).data()
        values = session.run(
            "MATCH (n {entity_type:'GiaTriQuyDinh'}) "
            "WHERE NOT (n)-[:DIRECTED {ontology_relation:'AP_DUNG_CHO'}]->() "
            "RETURN n.entity_id as name, coalesce(n.description,'') as desc"
        ).data()

    concept_names = [c["name"] for c in concepts]
    value_names = [v["name"] for v in values]
    value_desc = {v["name"]: v["desc"] for v in values}
    stats = {"values": len(value_names), "via_substring": 0, "via_embedding": 0, "unmatched": 0}
    if not concept_names or not value_names:
        return stats

    concept_texts = [_embed_text(c["name"], c["desc"]) for c in concepts]
    concept_embs = await _embed(concept_texts)
    unmatched_by_substring = []
    substring_links: list[tuple[str, str]] = []
    for name in value_names:
        match = _substring_match(name, concept_names)
        if match:
            substring_links.append((name, match))
            stats["via_substring"] += 1
        else:
            unmatched_by_substring.append(name)

    embedding_links: list[tuple[str, str]] = []
    if unmatched_by_substring:
        value_texts = [_embed_text(n, value_desc[n]) for n in unmatched_by_substring]
        value_embs = await _embed(value_texts)
        for name, emb in zip(unmatched_by_substring, value_embs):
            sims = [_cosine(emb, ce) for ce in concept_embs]
            best_idx = int(np.argmax(sims))
            if sims[best_idx] >= embedding_threshold:
                embedding_links.append((name, concept_names[best_idx]))
                stats["via_embedding"] += 1
            else:
                stats["unmatched"] += 1

    with driver.session() as session:
        for value_name, concept_name in substring_links + embedding_links:
            session.run(
                """
                MATCH (v {entity_id: $value}), (c {entity_id: $concept})
                MERGE (v)-[r:DIRECTED]->(c)
                ON CREATE SET r.ontology_relation = 'AP_DUNG_CHO', r.source = 'concept_linker.concept'
                """,
                value=value_name, concept=concept_name,
            )
    stats["links"] = substring_links + embedding_links
    return stats


async def main() -> None:
    driver = _driver()
    try:
        print("=== 1. link_provenance (file_path -> canonical VanBan, deterministic) ===")
        r1 = link_provenance(driver)
        print(f"  checked={r1['checked']} linked={r1['linked']} no_canonical_vanban={r1['no_canonical_vanban']}")

        print("\n=== 2. link_concepts (substring trước, embedding fallback) ===")
        r2 = await link_concepts(driver)
        print(f"  {r2['values']} value chưa có AP_DUNG_CHO -> "
              f"{r2['via_substring']} qua substring, {r2['via_embedding']} qua embedding, "
              f"{r2['unmatched']} không match nổi")
        for value, concept in r2.get("links", [])[:20]:
            print(f"    '{value}' -> '{concept}'")
    finally:
        driver.close()


if __name__ == "__main__":
    asyncio.run(main())
