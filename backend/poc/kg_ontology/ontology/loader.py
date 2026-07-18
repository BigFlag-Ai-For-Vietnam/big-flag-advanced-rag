"""Đọc entities.yaml + relations.yaml (sinh bởi build_ontology_yaml.py), dựng lại đúng
interface mà ontology_v1_bieuphi.py từng expose bằng Python dict cứng — để
ontology_graph_storage.py (Validator + Resolver, chặn trước khi ghi Neo4j) và
llm_adapter.py (entity_types_guidance cho LightRAG extractor) dùng chung 1 cách gọi,
không quan tâm ontology đến từ YAML hay hardcode.
"""
from __future__ import annotations

import os
import re

import yaml

_ONTOLOGY_DIR = os.path.dirname(__file__)
_ENTITIES_PATH = os.path.join(_ONTOLOGY_DIR, "entities.yaml")
_RELATIONS_PATH = os.path.join(_ONTOLOGY_DIR, "relations.yaml")


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} chưa tồn tại — chạy `python -m poc.kg_ontology.build_ontology_yaml` trước."
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_entities_doc = _load_yaml(_ENTITIES_PATH)
_relations_doc = _load_yaml(_RELATIONS_PATH)

# name -> mô tả ngắn (dùng build_entity_types_guidance())
ENTITY_TYPES: dict[str, str] = {
    name: spec.get("description", "") for name, spec in _entities_doc.get("entity_types", {}).items()
}

# name -> (mô tả, tuple keyword) — dùng classify_relation_keyword()
RELATION_TYPES: dict[str, tuple[str, tuple[str, ...]]] = {
    name: (spec.get("description", ""), tuple(spec.get("keywords", [])))
    for name, spec in _relations_doc.get("relation_types", {}).items()
}

# {(src_type, rel_type, tgt_type), ...} — cả 2 chiều vì quan hệ coi là vô hướng
ALLOWED_TRIPLES: set[tuple[str, str, str]] = set()
for _src, _rel, _tgt in _relations_doc.get("allowed_triples", []):
    ALLOWED_TRIPLES.add((_src, _rel, _tgt))
    ALLOWED_TRIPLES.add((_tgt, _rel, _src))

KNOWN_DOCUMENTS: list[dict] = _entities_doc.get("known_entities", {}).get("documents", [])
KNOWN_CONCEPTS: list[dict] = _entities_doc.get("known_entities", {}).get("concepts", [])
KNOWN_RELATIONS: list[dict] = _relations_doc.get("known_relations", [])

_ENTITY_TYPE_BY_CASEFOLD = {name.casefold(): name for name in ENTITY_TYPES}


def normalize_name(name: str) -> str:
    """Khoá so khớp/dedup entity name: gộp khoảng trắng + casefold."""
    return re.sub(r"\s+", " ", name or "").strip().casefold()


def canonical_entity_type(entity_type: str | None) -> str | None:
    """So khớp case-insensitive (LightRAG có thể lowercase entity_type khi ghi) rồi trả
    về tên chuẩn (khớp key ENTITY_TYPES/ALLOWED_TRIPLES), hoặc None nếu không khớp type nào."""
    if not entity_type:
        return None
    return _ENTITY_TYPE_BY_CASEFOLD.get(entity_type.casefold())


def classify_relation_keyword(keywords: str) -> str | None:
    """Map relationship_keywords tự do (LightRAG output) về 1 relation_type chuẩn hoá.

    Heuristic substring-match — đủ cho PoC, KHÔNG phải NLP chuẩn. Trả None nếu không
    khớp type nào -> caller (ontology_graph_storage) coi cạnh đó là ngoài ontology."""
    text = (keywords or "").casefold()
    for rel_type, (_desc, kw_list) in RELATION_TYPES.items():
        if any(kw.casefold() in text for kw in kw_list):
            return rel_type
    return None


def build_entity_types_guidance() -> str:
    """Format ENTITY_TYPES đúng style LightRAG dùng cho `default_entity_types_guidance`,
    feed vào addon_params["entity_types_guidance"]."""
    lines = ["Classify each entity using one of the following types. If no type fits, use `Other`.", ""]
    lines += [f"- {name}: {desc}" for name, desc in ENTITY_TYPES.items()]
    return "\n".join(lines)
