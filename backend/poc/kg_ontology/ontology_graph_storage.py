"""Validator + Entity Resolver CHẶN TRƯỚC KHI GHI Neo4j — đúng thứ tự
Extractor -> Validator -> Resolver -> Graph Writer, thay vì lọc hậu kỳ (post-hoc) như
bản PoC đầu tiên (noise_filter.py chạy SAU khi LightRAG đã ghi xong graph).

Cách làm: subclass Neo4JStorage, override upsert_node/upsert_edge để validate theo
ontology (ontology/loader.py) TRƯỚC khi gọi super() ghi thật — node/edge sai schema bị
DROP ÂM THẦM (không raise, không chặn cả pipeline), chỉ log lại để soát sau.

Đăng ký subclass này với LightRAG qua đường KHÔNG CÔNG KHAI (không có API chính thức để
truyền class trực tiếp) — `graph_storage` của LightRAG chỉ nhận STRING tên class, resolve
qua 2 dict nội bộ `lightrag.kg.STORAGES` (tên -> module path) và
`lightrag.kg.STORAGE_IMPLEMENTATIONS` (whitelist theo storage_type). Cả 2 đều là dict cấp
module, mutate được lúc runtime TRƯỚC khi tạo LightRAG(...) — đã verify trực tiếp trên
source `lightrag-hku==1.5.4` (kg/factory.py, kg/__init__.py). Đây KHÔNG phải API ổn định/
có tài liệu — gắn chặt với đúng version pin trong requirements-poc.txt, chấp nhận đánh
đổi này để lấy tốc độ (quyết định của người dùng, ưu tiên LightRAG hơn GraphRAG).

QUAN TRỌNG — rủi ro chưa verify được bằng đọc code, chỉ verify được bằng chạy thật:
nếu 1 node bị upsert_node() từ chối, NanoVectorDBStorage (entity vector-DB của LightRAG,
KHÔNG đi qua override này) có thể vẫn cứ index entity đó dù nó không tồn tại trong graph
-> lệch dữ liệu giữa graph và vector-DB nội bộ của LightRAG. run_kg_build.py phải quan
sát log DROP_LOG sau mỗi document để phát hiện sớm.
"""
from __future__ import annotations

import logging

from lightrag.kg import STORAGE_IMPLEMENTATIONS, STORAGES
from lightrag.kg.neo4j_impl import Neo4JStorage

from poc.kg_ontology.ontology.loader import ALLOWED_TRIPLES, canonical_entity_type, classify_relation_keyword

logger = logging.getLogger("ontology_graph_storage")

_STORAGE_NAME = "OntologyValidatingGraphStorage"
_MODULE_PATH = "poc.kg_ontology.ontology_graph_storage"  # path TUYỆT ĐỐI (không có "." đầu)

if _STORAGE_NAME not in STORAGE_IMPLEMENTATIONS["GRAPH_STORAGE"]["implementations"]:
    STORAGE_IMPLEMENTATIONS["GRAPH_STORAGE"]["implementations"].append(_STORAGE_NAME)
STORAGES[_STORAGE_NAME] = _MODULE_PATH

# Thu thập lại mọi lần drop để run_kg_build.py in báo cáo sau mỗi document — reset qua
# reset_drop_log() trước mỗi ainsert_custom_chunks().
DROP_LOG: list[dict] = []


def reset_drop_log() -> None:
    DROP_LOG.clear()


class OntologyValidatingGraphStorage(Neo4JStorage):
    """Neo4JStorage + validate theo ontology TRƯỚC khi ghi thật."""

    async def upsert_node(self, node_id: str, node_data: dict[str, str]) -> None:
        canonical = canonical_entity_type(node_data.get("entity_type"))
        if canonical is None:
            DROP_LOG.append(
                {"kind": "node", "node_id": node_id, "entity_type": node_data.get("entity_type")}
            )
            logger.info("DROP node '%s' — entity_type=%r không khớp ontology", node_id, node_data.get("entity_type"))
            return
        node_data["entity_type"] = canonical
        await super().upsert_node(node_id, node_data)

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]
    ) -> None:
        src_node = await self.get_node(source_node_id)
        tgt_node = await self.get_node(target_node_id)
        src_type = (src_node or {}).get("entity_type")
        tgt_type = (tgt_node or {}).get("entity_type")
        keywords = edge_data.get("keywords", "")
        rel_type = classify_relation_keyword(keywords)

        if src_node is None or tgt_node is None:
            DROP_LOG.append({
                "kind": "edge", "source": source_node_id, "target": target_node_id,
                "reason": "endpoint_missing", "src_found": src_node is not None, "tgt_found": tgt_node is not None,
            })
            logger.info(
                "DROP edge '%s'->'%s' — endpoint chưa tồn tại trong graph (src_found=%s tgt_found=%s)",
                source_node_id, target_node_id, src_node is not None, tgt_node is not None,
            )
            return

        if rel_type is None or (src_type, rel_type, tgt_type) not in ALLOWED_TRIPLES:
            DROP_LOG.append({
                "kind": "edge", "source": source_node_id, "target": target_node_id,
                "reason": "unclassified_relation" if rel_type is None else "invalid_triple",
                "keywords": keywords, "src_type": src_type, "tgt_type": tgt_type, "rel_type": rel_type,
            })
            logger.info(
                "DROP edge '%s'(%s) -[%s / kw=%r]-> '%s'(%s) — ngoài ontology",
                source_node_id, src_type, rel_type, keywords, target_node_id, tgt_type,
            )
            return

        edge_data["ontology_relation"] = rel_type
        await super().upsert_edge(source_node_id, target_node_id, edge_data)
