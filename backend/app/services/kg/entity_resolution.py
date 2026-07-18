"""Entity Resolver — chạy SAU khi graph đã build cho 1 document (post-processing pass trên
Neo4j), gộp node trùng nhưng bị extract dưới nhiều tên khác nhau. 2 tier khác hẳn nhau,
không dùng chung 1 cơ chế:

- VanBan: có khoá tự nhiên (số hiệu văn bản, vd "09/2024/TT-NHNN") xuất hiện y hệt trong
  MỌI biến thể tên — gộp bằng regex, KHÔNG cần LLM, chính xác gần tuyệt đối.
- KhaiNiem / GiaTriQuyDinh: không có khoá tự nhiên — gộp bằng candidate generation rẻ
  (cosine similarity trên embedding) rồi CHỈ gọi LLM xác nhận trên các cặp candidate
  (không so N² cặp).

Nhận `Driver` từ caller (build_service.py sở hữu vòng đời driver) — không tự mở/đóng
connection ở đây.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
from neo4j import Driver

from app.services.kg.llm_adapter import _embed, llm_model_func
from app.services.kg.so_hieu import SO_HIEU_RE  # noqa: F401 — re-exported cho code cũ import từ đây

_MERGE_TAG = "<MERGED_FROM>"


def merge_node(session, keep_id: str, drop_id: str) -> None:
    """Dồn toàn bộ cạnh (vào + ra) của `drop_id` sang `keep_id`, giữ lại description +
    alias, rồi xoá node `drop_id`. Quan hệ Neo4j của LightRAG luôn có type "DIRECTED",
    ý nghĩa thật nằm ở property `ontology_relation`/`keywords` — copy nguyên property."""
    if keep_id == drop_id:
        return
    session.run(
        """
        MATCH (drop {entity_id: $drop_id})-[r]->(other)
        WHERE other.entity_id <> $keep_id
        MATCH (keep {entity_id: $keep_id})
        MERGE (keep)-[r2:DIRECTED]->(other)
        ON CREATE SET r2 = properties(r)
        """,
        keep_id=keep_id, drop_id=drop_id,
    )
    session.run(
        """
        MATCH (other)-[r]->(drop {entity_id: $drop_id})
        WHERE other.entity_id <> $keep_id
        MATCH (keep {entity_id: $keep_id})
        MERGE (other)-[r2:DIRECTED]->(keep)
        ON CREATE SET r2 = properties(r)
        """,
        keep_id=keep_id, drop_id=drop_id,
    )
    session.run(
        f"""
        MATCH (drop {{entity_id: $drop_id}}), (keep {{entity_id: $keep_id}})
        SET keep.description = keep.description + ' {_MERGE_TAG} ' + coalesce(drop.description, ''),
            keep.aliases = coalesce(keep.aliases, []) + [drop.entity_id]
        DETACH DELETE drop
        """,
        keep_id=keep_id, drop_id=drop_id,
    )


def dedupe_parallel_relations(driver: Driver, ontology_relation: str) -> dict:
    """Gộp cạnh song song 2 chiều CÙNG ontology_relation giữa CÙNG 1 cặp node (vd LightRAG
    tự trích 1 THAY_THE không property đặc thù + citation_extractor ghi thêm 1 THAY_THE
    ngược chiều có property partial/giu_hieu_luc) — LUÔN ưu tiên bản có
    partial/giu_hieu_luc/uu_tien_cho/loai (property riêng của citation_extractor, đáng tin
    hơn cho quan hệ document-to-document — xem citation_extractor.py); nếu cả 2 đều không
    có (hoặc cả 2 đều có) thì mới so tổng số key làm tiêu chí phụ. Coi quan hệ là vô
    hướng (đúng model LightRAG), không tự suy đoán chiều đúng."""
    _PREFERRED_KEYS = ["partial", "giu_hieu_luc", "uu_tien_cho", "loai"]
    with driver.session() as session:
        pairs = session.run(
            """
            MATCH (a)-[r1]->(b)
            WHERE r1.ontology_relation = $rel AND elementId(a) < elementId(b)
            OPTIONAL MATCH (b)-[r2]->(a) WHERE r2.ontology_relation = $rel
            RETURN a.entity_id as a, b.entity_id as b,
                   elementId(r1) as r1_id, properties(r1) as r1_props,
                   elementId(r2) as r2_id, properties(r2) as r2_props
            """,
            rel=ontology_relation,
        ).data()

        def _has_citation_props(props: dict) -> bool:
            return any(props.get(k) not in (None, "") for k in _PREFERRED_KEYS)

        removed = []
        for p in pairs:
            if p["r2_id"] is None:
                continue
            r1_special, r2_special = _has_citation_props(p["r1_props"]), _has_citation_props(p["r2_props"])
            if r1_special != r2_special:
                drop_id = p["r2_id"] if r1_special else p["r1_id"]
            else:
                drop_id = p["r2_id"] if len(p["r1_props"]) >= len(p["r2_props"]) else p["r1_id"]
            session.run("MATCH ()-[r]->() WHERE elementId(r) = $id DELETE r", id=drop_id)
            removed.append((p["a"], p["b"]))
        return {"pairs_checked": len(pairs), "removed": removed}


# ------------------------------------------------------------------ Tier 1: VanBan (regex)

def resolve_vanban(driver: Driver) -> dict:
    """Gộp VanBan node theo số hiệu trích bằng regex — deterministic, không LLM."""
    with driver.session() as session:
        rows = session.run(
            "MATCH (n {entity_type: 'VanBan'}) "
            "RETURN n.entity_id as name, size(coalesce(n.description,'')) as desc_len, "
            "size([(n)--() | 1]) as degree"
        ).data()

        groups: dict[str, list[dict]] = {}
        for row in rows:
            m = SO_HIEU_RE.search(row["name"])
            if not m:
                continue
            groups.setdefault(m.group(0), []).append(row)

        merges = []
        for so_hieu, members in groups.items():
            if len(members) < 2:
                continue
            # canonical = degree cao nhất, hoà thì description dài nhất
            keep = max(members, key=lambda r: (r["degree"], r["desc_len"]))["name"]
            for m in members:
                if m["name"] != keep:
                    merge_node(session, keep, m["name"])
                    merges.append((so_hieu, m["name"], keep))
        return {"so_hieu_groups": len(groups), "merges": merges}


# ------------------------------------------------------------------ Tier 2: KhaiNiem/GiaTriQuyDinh
# (candidate qua cosine similarity, xác nhận qua LLM — không so N² cặp)

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


async def _confirm_pair_llm(name_a: str, desc_a: str, name_b: str, desc_b: str) -> bool:
    prompt = (
        "2 tên entity dưới đây có phải CÙNG 1 khái niệm/giá trị thực tế trong tài liệu "
        "tuân thủ ngân hàng không (chỉ khác cách LLM viết hoa/diễn đạt), hay là 2 thứ "
        "khác nhau thật sự?\n\n"
        f"A: \"{name_a}\" — {desc_a[:200]}\n"
        f"B: \"{name_b}\" — {desc_b[:200]}\n\n"
        "Trả lời CHỈ 1 từ: CUNG (nếu cùng 1 thực thể) hoặc KHAC (nếu khác nhau)."
    )
    resp = await llm_model_func(prompt, temperature=0.0, max_tokens=10)
    return resp.strip().upper().startswith("CUNG")


async def resolve_fuzzy_concepts(
    driver: Driver, entity_type: str, threshold: float = 0.88, max_candidates: int = 60
) -> dict:
    """Gộp node cùng entity_type có embedding gần nhau (candidate) rồi LLM xác nhận."""
    with driver.session() as session:
        rows = session.run(
            "MATCH (n {entity_type: $t}) RETURN n.entity_id as name, coalesce(n.description,'') as desc",
            t=entity_type,
        ).data()

    if len(rows) < 2:
        return {"nodes": len(rows), "candidates": 0, "merges": []}

    names = [r["name"] for r in rows]
    descs = {r["name"]: r["desc"] for r in rows}
    embeddings = await _embed(names)  # embed theo tên — rẻ, đủ cho việc gộp fuzzy-name

    candidates = []
    for (i, a), (j, b) in combinations(enumerate(names), 2):
        sim = _cosine(embeddings[i], embeddings[j])
        if sim >= threshold:
            candidates.append((sim, a, b))
    candidates.sort(reverse=True)
    candidates = candidates[:max_candidates]

    # union-find để gộp bắc cầu (A~B, B~C => A,B,C cùng nhóm)
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    confirmed = []
    for sim, a, b in candidates:
        if find(a) == find(b):
            continue
        is_same = await _confirm_pair_llm(a, descs[a], b, descs[b])
        if is_same:
            union(a, b)
            confirmed.append((sim, a, b))

    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)

    with driver.session() as session:
        merges = []
        for _root, members in groups.items():
            if len(members) < 2:
                continue
            keep = max(members, key=lambda n: len(descs[n]))
            for m in members:
                if m != keep:
                    merge_node(session, keep, m)
                    merges.append((m, keep))
        return {
            "nodes": len(rows), "candidates": len(candidates),
            "confirmed_pairs": confirmed, "merges": merges,
        }
