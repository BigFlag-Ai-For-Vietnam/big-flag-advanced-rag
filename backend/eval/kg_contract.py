"""Import KnowledgeGraph ngoài (do đồng nghiệp xây, chưa xong) theo contract v1
(backend/eval/schemas/kg_contract_v1.schema.json) vào ragas KnowledgeGraph.

Không import ragas ở top-level module (NFR-1/NFR-2): load_contract/validate_contract
là thuần Python; chỉ contract_to_kg mới cần kiểu Node/Relationship của ragas (import trễ).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
# Phải khớp key mà T08 (chunk-source-kg-build) đặt lên node CHUNK — xem
# eval/dataset_source.py::build_kg: node.properties["document_metadata"]["chunk_id"].
CHUNK_ID_PROPERTY = "chunk_id"
ENTITIES_PROPERTY = "entities"          # property MultiHopSpecificQuerySynthesizer đọc
OVERLAP_REL_TYPE = "entities_overlap"   # relation_type mặc định của MultiHopSpecificQuerySynthesizer


class KGContractError(ValueError):
    """Contract KG ngoài sai định dạng — nêu rõ field thiếu/sai."""


def load_contract(path: str | Path) -> dict:
    """Đọc file --kg-file (JSON host-local, giống personas.json), validate, trả dict.
    KHÔNG đi qua storage_service: đây là input CLI trên host, không phải blob tài liệu."""
    p = Path(path)
    if not p.exists():
        raise KGContractError(f"Không tìm thấy file KG contract tại '{p}'.")
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_contract(data)
    return data


def validate_contract(data: dict) -> None:
    """Fail-fast: raise KGContractError liệt kê tên field còn thiếu/sai kiểu."""
    if not isinstance(data, dict):
        raise KGContractError("KG contract phải là một object JSON.")
    if data.get("version") != CONTRACT_VERSION:
        raise KGContractError(f"KG contract thiếu hoặc sai 'version' (yêu cầu {CONTRACT_VERSION}).")
    if "entities" not in data or not isinstance(data["entities"], list):
        raise KGContractError("KG contract thiếu field 'entities' (phải là list).")
    if "relations" not in data or not isinstance(data["relations"], list):
        raise KGContractError("KG contract thiếu field 'relations' (phải là list).")

    entity_ids = set()
    for i, entity in enumerate(data["entities"]):
        for field in ("id", "name", "type"):
            if field not in entity:
                raise KGContractError(f"entities[{i}] thiếu field '{field}'.")
        entity_ids.add(entity["id"])

    for i, relation in enumerate(data["relations"]):
        for field in ("source", "target", "type"):
            if field not in relation:
                raise KGContractError(f"relations[{i}] thiếu field '{field}'.")
        if relation["source"] not in entity_ids:
            raise KGContractError(f"relations[{i}].source '{relation['source']}' không khớp entity id nào.")
        if relation["target"] not in entity_ids:
            raise KGContractError(f"relations[{i}].target '{relation['target']}' không khớp entity id nào.")


def contract_to_kg(data: dict, kg: Any) -> Any:
    """Gắn entity vào node CHUNK khớp chunk_id; sinh Relationship 'entities_overlap'
    giữa các chunk mà 2 entity của một relation trỏ tới. Mutate + trả về kg."""
    from ragas.testset.graph import NodeType, Relationship

    validate_contract(data)

    chunk_nodes_by_id = {
        n.properties.get("document_metadata", {}).get(CHUNK_ID_PROPERTY): n
        for n in kg.nodes
        if n.type == NodeType.CHUNK and n.properties.get("document_metadata", {}).get(CHUNK_ID_PROPERTY)
    }

    entities_by_id = {e["id"]: e for e in data["entities"]}
    chunk_ids_by_entity: dict[str, set[str]] = {}
    for entity in data["entities"]:
        linked_chunks = set()
        for chunk_id in entity.get("chunk_ids", []):
            node = chunk_nodes_by_id.get(chunk_id)
            if node is None:
                continue
            node.properties.setdefault(ENTITIES_PROPERTY, [])
            if entity["name"] not in node.properties[ENTITIES_PROPERTY]:
                node.properties[ENTITIES_PROPERTY].append(entity["name"])
            node.properties.setdefault("kg_entities", [])
            node.properties["kg_entities"].append(entity)
            linked_chunks.add(chunk_id)
        chunk_ids_by_entity[entity["id"]] = linked_chunks

    for relation in data["relations"]:
        src_entity = entities_by_id[relation["source"]]
        tgt_entity = entities_by_id[relation["target"]]
        src_chunk_ids = chunk_ids_by_entity.get(relation["source"], set())
        tgt_chunk_ids = chunk_ids_by_entity.get(relation["target"], set())
        for src_chunk_id in src_chunk_ids:
            for tgt_chunk_id in tgt_chunk_ids:
                if src_chunk_id == tgt_chunk_id:
                    continue
                src_node = chunk_nodes_by_id[src_chunk_id]
                tgt_node = chunk_nodes_by_id[tgt_chunk_id]
                kg.add(Relationship(
                    source=src_node,
                    target=tgt_node,
                    type=OVERLAP_REL_TYPE,
                    bidirectional=True,
                    properties={
                        "overlapped_items": [[src_entity["name"], tgt_entity["name"]]],
                        "entities_overlap_score": 1.0,
                        "kg_relation_type": relation["type"],
                    },
                ))

    return kg
