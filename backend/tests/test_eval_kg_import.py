"""Test import KG ngoài theo contract v1 (FR-2) — offline, đồ thị thuần."""
import pytest

pytest.importorskip("ragas")

from eval.kg_contract import CHUNK_ID_PROPERTY, KGContractError, contract_to_kg


def _build_two_chunk_kg():
    from ragas.testset.graph import KnowledgeGraph, Node, NodeType

    kg = KnowledgeGraph()
    kg.add(Node(type=NodeType.CHUNK, properties={
        "page_content": "Phí thường niên là 500.000đ.",
        "document_metadata": {CHUNK_ID_PROPERTY: "c1", "document_id": "d1", "title": "T", "chunk_index": 0},
    }))
    kg.add(Node(type=NodeType.CHUNK, properties={
        "page_content": "Điều kiện mở thẻ tín dụng.",
        "document_metadata": {CHUNK_ID_PROPERTY: "c2", "document_id": "d1", "title": "T", "chunk_index": 1},
    }))
    return kg


def test_contract_json_to_ragas_kg():
    from ragas.testset.synthesizers import MultiHopSpecificQuerySynthesizer

    kg = _build_two_chunk_kg()
    contract = {
        "version": 1,
        "entities": [
            {"id": "e1", "name": "Phí thường niên", "type": "Fee", "chunk_ids": ["c1"]},
            {"id": "e2", "name": "Điều kiện mở thẻ", "type": "Condition", "chunk_ids": ["c2"]},
        ],
        "relations": [
            {"source": "e1", "target": "e2", "type": "applies_to"},
        ],
    }

    result_kg = contract_to_kg(contract, kg)

    chunk_nodes = list(result_kg.nodes)
    entities_by_chunk = {
        n.properties["document_metadata"][CHUNK_ID_PROPERTY]: n.properties.get("entities", [])
        for n in chunk_nodes
    }
    assert "Phí thường niên" in entities_by_chunk["c1"]
    assert "Điều kiện mở thẻ" in entities_by_chunk["c2"]

    overlap_rels = [r for r in result_kg.relationships if r.type == "entities_overlap"]
    assert len(overlap_rels) >= 1

    synth = MultiHopSpecificQuerySynthesizer(llm=object())
    clusters = synth.get_node_clusters(result_kg)
    assert len(clusters) >= 1


def test_invalid_contract_rejected():
    contract = {
        "version": 1,
        "entities": [{"id": "e1", "name": "Phí thường niên", "type": "Fee"}],
        # missing "relations"
    }
    with pytest.raises(KGContractError, match="relations"):
        contract_to_kg(contract, _build_two_chunk_kg())
