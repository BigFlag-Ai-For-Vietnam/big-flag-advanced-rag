"""Orchestrator: chạy Entity Resolver + Citation Extractor lên graph ĐÃ CÓ SẴN trong
Neo4j (không build lại KG). Thứ tự BẮT BUỘC:

  1. resolve_vanban()        — gộp VanBan trùng (regex số hiệu) TRƯỚC, để bước 2 ghi
                                đúng vào node canonical, không tạo thêm bản trùng.
  2. citation_extractor.run() — thêm edge CAN_CU/THAM_CHIEU/THAY_THE/UU_TIEN_HON xác
                                định (deterministic), bổ sung cho phần LightRAG trích
                                thiếu/không đáng tin ở loại quan hệ document-to-document.
  3. resolve_fuzzy_concepts() — gộp KhaiNiem/GiaTriQuyDinh trùng (embedding + LLM confirm),
                                chạy sau cùng vì tốn LLM call, không phụ thuộc bước 1-2.

Chạy (từ backend/, cần Neo4j đang chạy với graph đã build qua run_kg_build.py):
    NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=<pass> \
        python -m poc.kg_ontology.run_resolve_and_citations
"""
from __future__ import annotations

import asyncio
import os
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from poc.kg_ontology import citation_extractor  # noqa: E402
from poc.kg_ontology.entity_resolution import _driver, resolve_fuzzy_concepts, resolve_vanban  # noqa: E402


def _counts(driver) -> dict:
    with driver.session() as s:
        nodes = s.run("MATCH (n) RETURN count(n) as c").single()["c"]
        edges = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
    return {"nodes": nodes, "edges": edges}


async def main() -> None:
    driver = _driver()
    try:
        before = _counts(driver)
        print(f"Trước: {before['nodes']} node, {before['edges']} edge\n")

        print("### BƯỚC 1 — resolve_vanban (regex số hiệu, không LLM) ###")
        r1 = resolve_vanban(driver)
        print(f"{r1['so_hieu_groups']} nhóm số hiệu, {len(r1['merges'])} node gộp")
        for so_hieu, dropped, keep in r1["merges"]:
            print(f"  [{so_hieu}] '{dropped}' -> '{keep}'")

        print("\n### BƯỚC 2 — citation_extractor (regex + verb context, không LLM) ###")
        r2 = citation_extractor.run(driver)
        print(f"Quét {r2['scanned_docs']} doc, {r2['citations_found']} citation, "
              f"{r2['edges_written']} edge ghi. Theo loại: {r2['by_type']}")

        print("\n### BƯỚC 3a — resolve_fuzzy_concepts KhaiNiem (embedding + LLM confirm) ###")
        r3 = await resolve_fuzzy_concepts(driver, "KhaiNiem")
        print(f"{r3['nodes']} node, {r3['candidates']} candidate, {len(r3['merges'])} gộp")
        for dropped, keep in r3["merges"]:
            print(f"  '{dropped}' -> '{keep}'")

        print("\n### BƯỚC 3b — resolve_fuzzy_concepts GiaTriQuyDinh (embedding + LLM confirm) ###")
        r4 = await resolve_fuzzy_concepts(driver, "GiaTriQuyDinh")
        print(f"{r4['nodes']} node, {r4['candidates']} candidate, {len(r4['merges'])} gộp")
        for dropped, keep in r4["merges"]:
            print(f"  '{dropped}' -> '{keep}'")

        after = _counts(driver)
        print(f"\n=== Tổng kết ===")
        print(f"Trước: {before['nodes']} node, {before['edges']} edge")
        print(f"Sau:   {after['nodes']} node, {after['edges']} edge")
    finally:
        driver.close()


if __name__ == "__main__":
    asyncio.run(main())
