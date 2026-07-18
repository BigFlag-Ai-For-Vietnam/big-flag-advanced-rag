"""Post-processing "Ontology Validation & Filtering" layer (arXiv:2507.06107 gọi đây là
bước bắt buộc giữa Extraction và Graph Assembly) — áp lên graph LightRAG đã build ra.

LightRAG tự lo phần "Schema Definition -> Extraction" cho ENTITY (qua
`entity_types_guidance`, xem ontology.py + llm_adapter.py) nhưng KHÔNG có validation
layer nào sau đó: node/edge model trả về sai type hoặc quan hệ vô nghĩa vẫn được ghi
thẳng vào graph. File này bù đúng phần thiếu đó, 2 bước áp tuần tự:

1. canonicalize_graph  — entity resolution: gộp node trùng tên (khác hoa/thường,
   khoảng trắng) — vá đúng ca "John Doe, 45" vs "John Doe, age 45" mà bài Medium mô tả.
2. apply_ontology_filter — schema compliance filter: loại node sai entity_type, loại
   edge có relation không map được về ontology hoặc (src_type, relation, tgt_type)
   không nằm trong ALLOWED_TRIPLES, rồi loại node mồ côi (degree 0) phát sinh sau khi
   lọc edge.

Trả kèm `stats` dict để run_poc.py in báo cáo before/after — mục đích PoC là CHỨNG MINH
lượng noise giảm được, không phải tối ưu thuật toán merge (dùng string-normalize đơn
giản, không dùng embedding similarity/fuzzy match — ghi rõ là giới hạn PoC).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from poc.kg_ontology.ontology_v1_bieuphi import (
    ALLOWED_TRIPLES,
    canonical_entity_type,
    classify_relation_keyword,
    normalize_name,
)


@dataclass
class FilterStats:
    nodes_before: int = 0
    edges_before: int = 0
    nodes_merged: int = 0
    nodes_dropped_bad_type: int = 0
    edges_dropped_unclassified_relation: int = 0
    edges_dropped_invalid_triple: int = 0
    nodes_dropped_orphan: int = 0
    nodes_after: int = 0
    edges_after: int = 0
    dropped_node_examples: list[str] = field(default_factory=list)
    dropped_edge_examples: list[str] = field(default_factory=list)


def canonicalize_graph(G: nx.Graph) -> tuple[nx.Graph, int]:
    """Gộp node có cùng normalize_name(entity_name) — giữ lại node có description dài
    hơn (thường là bản đầy đủ hơn), dồn edge của các node bị gộp sang node giữ lại."""
    buckets: dict[str, list[str]] = {}
    for node_id in G.nodes():
        key = normalize_name(node_id)
        buckets.setdefault(key, []).append(node_id)

    merged_count = 0
    out = G.copy()
    for _key, members in buckets.items():
        if len(members) < 2:
            continue
        members_sorted = sorted(
            members, key=lambda n: len(out.nodes[n].get("description", "") or ""), reverse=True
        )
        keep, drops = members_sorted[0], members_sorted[1:]
        for drop in drops:
            if drop not in out:
                continue
            for _, nbr, edata in out.edges(drop, data=True):
                if nbr == keep:
                    continue
                if out.has_edge(keep, nbr):
                    out[keep][nbr]["weight"] = float(out[keep][nbr].get("weight", 1) or 1) + float(
                        edata.get("weight", 1) or 1
                    )
                else:
                    out.add_edge(keep, nbr, **edata)
            out.remove_node(drop)
            merged_count += 1
    return out, merged_count


def apply_ontology_filter(G: nx.Graph) -> tuple[nx.Graph, FilterStats]:
    stats = FilterStats(nodes_before=G.number_of_nodes(), edges_before=G.number_of_edges())
    out = G.copy()

    # 1) type validation cho node — loại node có entity_type ngoài ontology (bao gồm
    #    "Other"/"UNKNOWN" mà LightRAG tự gán khi model không map được type nào).
    #    canonical_entity_type() so khớp case-insensitive rồi ghi lại type chuẩn PascalCase
    #    lên node (LightRAG lowercase entity_type khi ghi vào graph) để bước 2 (triple
    #    check) và visualize.py (map màu theo ENTITY_TYPES) dùng đúng.
    for node_id, data in list(out.nodes(data=True)):
        canonical = canonical_entity_type(data.get("entity_type"))
        if canonical is None:
            stats.nodes_dropped_bad_type += 1
            if len(stats.dropped_node_examples) < 15:
                stats.dropped_node_examples.append(f"{node_id} (entity_type={data.get('entity_type')!r})")
            out.remove_node(node_id)
        else:
            out.nodes[node_id]["entity_type"] = canonical

    # 2) relation validity cho edge — map keywords tự do -> relation_type chuẩn hoá,
    #    rồi check (src_type, relation_type, tgt_type) có hợp lệ không.
    for u, v, data in list(out.edges(data=True)):
        keywords = data.get("keywords", "")
        rel_type = classify_relation_keyword(keywords)
        if rel_type is None:
            stats.edges_dropped_unclassified_relation += 1
            if len(stats.dropped_edge_examples) < 15:
                stats.dropped_edge_examples.append(f"{u} -[{keywords}]-> {v} (không map được relation type)")
            out.remove_edge(u, v)
            continue
        src_type = out.nodes[u].get("entity_type")
        tgt_type = out.nodes[v].get("entity_type")
        if (src_type, rel_type, tgt_type) not in ALLOWED_TRIPLES:
            stats.edges_dropped_invalid_triple += 1
            if len(stats.dropped_edge_examples) < 15:
                stats.dropped_edge_examples.append(
                    f"{u} ({src_type}) -[{rel_type}]-> {v} ({tgt_type}) — triple không hợp lệ"
                )
            out.remove_edge(u, v)
        else:
            out.edges[u, v]["ontology_relation"] = rel_type

    # 3) prune orphan phát sinh sau bước 2 (node còn type hợp lệ nhưng mất hết cạnh).
    for node_id in list(out.nodes()):
        if out.degree(node_id) == 0:
            stats.nodes_dropped_orphan += 1
            out.remove_node(node_id)

    stats.nodes_after = out.number_of_nodes()
    stats.edges_after = out.number_of_edges()
    return out, stats
