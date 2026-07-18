"""Build knowledge graph vào Neo4j từ 10 document đã ingest (ingest_corpus.py) — 10 lần
`ainsert()`, MỖI DOCUMENT 1 LẦN, input = nối các Chunk.final_content (đã contextual) của
đúng document đó thành 1 text, `ids=doc.id` để giữ đúng UUID app thật (provenance).
graph_storage = OntologyValidatingGraphStorage (Validator + Resolver chặn TRƯỚC khi ghi,
xem ontology_graph_storage.py).

(Ban đầu dùng `ainsert_custom_chunks()` để giữ đúng ranh giới chunk của app thật — nhưng
method đó bị đánh dấu deprecated trong lightrag-hku==1.5.4 và KHÔNG chạy bước merge-vào-
graph (verify bằng đọc source + chạy thật: 10/10 doc "insert xong" nhưng Neo4j 0 node) —
đổi sang `ainsert()`, đường được test đầy đủ.)

Chạy (từ backend/, cần Neo4j đang chạy + FPT_API_KEY):
    NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=<pass> \
        python -m poc.kg_ontology.run_kg_build
"""
from __future__ import annotations

import asyncio
import os
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Chunk, Document  # noqa: E402

# import NÀY PHẢI đứng TRƯỚC khi tạo LightRAG(...) — nó monkeypatch STORAGES/
# STORAGE_IMPLEMENTATIONS để "OntologyValidatingGraphStorage" resolve được.
from poc.kg_ontology import ontology_graph_storage  # noqa: E402,F401
from poc.kg_ontology.llm_adapter import build_embedding_func, llm_model_func  # noqa: E402
from poc.kg_ontology.ontology.loader import build_entity_types_guidance  # noqa: E402
from poc.kg_ontology.ontology_graph_storage import DROP_LOG, reset_drop_log  # noqa: E402

from lightrag import LightRAG  # noqa: E402
from lightrag.kg.shared_storage import initialize_pipeline_status  # noqa: E402

_WORKING_DIR = os.path.join(os.path.dirname(__file__), "_kg_storage", "compliance")


def _load_documents() -> list[tuple[Document, list[Chunk]]]:
    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.category == "tuan_thu")
            .order_by(Document.title)
            .all()
        )
        out = []
        for doc in docs:
            chunks = (
                db.query(Chunk)
                .filter(Chunk.document_id == doc.id)
                .order_by(Chunk.chunk_index)
                .all()
            )
            out.append((doc, chunks))
        return out
    finally:
        db.close()


def _drop_summary() -> dict:
    by_reason: dict[str, int] = {}
    for item in DROP_LOG:
        key = item.get("reason") or ("bad_type" if item["kind"] == "node" else "?")
        by_reason[key] = by_reason.get(key, 0) + 1
    return by_reason


async def main() -> None:
    if not settings.fpt_api_key:
        raise SystemExit("FPT_API_KEY chưa cấu hình (.env).")
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"):
        if not os.environ.get(var):
            raise SystemExit(f"{var} chưa set — cần Neo4j đang chạy (xem docstring đầu file).")

    os.makedirs(_WORKING_DIR, exist_ok=True)
    documents = _load_documents()
    if not documents:
        raise SystemExit("Không tìm thấy document category=tuan_thu — chạy ingest_corpus.py trước.")
    print(f"Sẽ build KG cho {len(documents)} document vào Neo4j ({os.environ['NEO4J_URI']})")

    rag = LightRAG(
        working_dir=_WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=build_embedding_func(),
        graph_storage="OntologyValidatingGraphStorage",
        addon_params={
            "language": "Vietnamese",
            "entity_types_guidance": build_entity_types_guidance(),
        },
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()

    total_drops: dict[str, int] = {}
    for i, (doc, chunks) in enumerate(documents, start=1):
        if not chunks:
            print(f"[{i}/{len(documents)}] {doc.title} — KHÔNG có chunk, bỏ qua")
            continue
        print(f"\n[{i}/{len(documents)}] {doc.title} ({len(chunks)} chunk) doc_id={doc.id}")
        # ainsert_custom_chunks() bị đánh dấu deprecated trong lightrag-hku==1.5.4 và (verify
        # bằng đọc source + chạy thật) KHÔNG chạy bước merge-vào-graph — chunk_results của
        # _process_extract_entities() bị bỏ luôn, upsert_node/upsert_edge không bao giờ được
        # gọi (đã confirm: 10/10 doc "thành công" nhưng Neo4j 0 node). Dùng ainsert() (đường
        # được test đầy đủ) — nối các final_content (đã contextual) lại thành 1 text, để
        # LightRAG tự re-chunk; câu định vị vẫn còn trong text nên không mất ngữ cảnh liên
        # văn bản, chỉ không giữ đúng y hệt ranh giới chunk của app thật nữa.
        full_text = "\n\n".join(c.final_content for c in chunks)

        reset_drop_log()
        await rag.ainsert(full_text, ids=doc.id, file_paths=doc.title)

        summary = _drop_summary()
        for k, v in summary.items():
            total_drops[k] = total_drops.get(k, 0) + v
        if summary:
            print(f"    dropped: {summary}")
        else:
            print("    dropped: (không có gì bị loại)")

    await rag.finalize_storages()

    print("\n=== Tổng kết drop toàn bộ 10 document ===")
    print(total_drops or "(không có gì bị loại)")
    print(f"\nWorking dir (KV/vector cache): {_WORKING_DIR}")
    print("Xem graph trong Neo4j Browser: http://localhost:7474")


if __name__ == "__main__":
    asyncio.run(main())
