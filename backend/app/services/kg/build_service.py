"""Orchestration cho graph-build 1 document — chạy NỀN trên 1 event loop dùng chung, sống
suốt vòng đời process (xem `_get_loop()`), KHÔNG chặn Qdrant indexing (Stage C của
pipeline.py chạy ngay sau khi `submit_graph_build()` trả về, không đợi). Chỉ được gọi từ
`pipeline.py` khi `kg_enable_build=True` và `document.category` thuộc `kg_categories`
(mặc định chỉ "tuan_thu" — ontology hiện chỉ verify đúng domain này).

Thứ tự bắt buộc (Extractor -> Validator/Resolver -> Graph Writer đã nằm trong
`graph_storage.OntologyValidatingGraphStorage`; phần dưới đây là hậu xử lý SAU khi
LightRAG ghi xong):
  1. LightRAG ainsert() — entity/relation tự do, validate + ghi qua OntologyValidatingGraphStorage
  2. entity_resolution.resolve_vanban() — gộp VanBan trùng theo số hiệu (regex, không LLM)
  3. stamp document_id thật lên node (file_path=title AND document_id IS NULL) — PHẢI SAU (2),
     nếu không node bị merge/xoá ở (2) sẽ mang document_id sai
  4. citation_extractor.run_for_document() — CĂN_CỨ/THAY_THẾ/THAM_CHIẾU/ƯU_TIÊN_HƠN (regex, không LLM)
  5. entity_resolution.dedupe_parallel_relations() mỗi citation relation type
  6-7. entity_resolution.resolve_fuzzy_concepts() cho KhaiNiem rồi GiaTriQuyDinh (embedding + LLM confirm)
  8-9. concept_linker.link_provenance() + link_concepts() — vá orphan value/concept node

Rủi ro đã xác nhận & chấp nhận (v1 shortcut, không che giấu): thread nền này sống ngoài
vòng đời `run_pipeline()`; nếu process restart giữa chừng, `graph_status` kẹt ở
`"building"` vĩnh viễn cho document đó — không xây full crash-recovery (đúng tinh thần
"BackgroundTasks thay Celery, hướng nâng cấp v2" đã ghi trong pipeline.py). Giảm nhẹ bằng
cách cho phép trigger lại thủ công (reprocess document).
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading

from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from neo4j import GraphDatabase

from app.config import settings
from app.db import SessionLocal
from app.models import Document, GraphStatus

# import NÀY PHẢI đứng TRƯỚC khi tạo LightRAG(...) — nó monkeypatch STORAGES/
# STORAGE_IMPLEMENTATIONS để "OntologyValidatingGraphStorage" resolve được (xem graph_storage.py).
from app.services.kg import graph_storage  # noqa: F401
from app.services.kg import citation_extractor, concept_linker, entity_resolution
from app.services.kg.llm_adapter import build_embedding_func, llm_model_func
from app.services.kg.ontology.loader import build_entity_types_guidance

logger = logging.getLogger("kg.build_service")

_WORKING_DIR = os.path.join(settings.data_dir, "kg_lightrag_storage")

# 1 event loop DUY NHẤT, sống suốt vòng đời process, chạy trong 1 thread nền riêng —
# KHÔNG dùng asyncio.run() mỗi lần build (đã vỡ thật lúc test tải: LightRAG's
# shared_storage giữ asyncio.Lock() global cấp MODULE, 1 khi bound vào 1 event loop thì
# mọi lần acquire SAU đó phải cùng loop, nếu không crash "bound to a different event
# loop" — asyncio.run() tạo loop mới mỗi lần gọi nên document build thứ 2 trở đi luôn
# crash). Semaphore (tạo lazy TRONG loop) giới hạn số build chạy đồng thời = kg_max_concurrent_builds.
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()
_semaphore: asyncio.Semaphore | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is not None:
        return _loop
    with _loop_lock:
        if _loop is not None:
            return _loop
        ready = threading.Event()

        def _run() -> None:
            global _loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _loop = loop
            ready.set()
            loop.run_forever()

        threading.Thread(target=_run, name="kg-build-loop", daemon=True).start()
        ready.wait()
        return _loop


async def _get_semaphore() -> asyncio.Semaphore:
    # asyncio.Semaphore bind vào loop hiện hành lúc khởi tạo — PHẢI tạo lazy bên trong 1
    # coroutine đang chạy trên _loop, không tạo ở module level (loop chưa tồn tại lúc import).
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.kg_max_concurrent_builds)
    return _semaphore


def submit_graph_build(document_id: str, title: str, chunk_texts: list[str]) -> None:
    """Điểm vào cho pipeline.py — trả về NGAY, build chạy nền trên event loop dùng chung."""
    loop = _get_loop()
    asyncio.run_coroutine_threadsafe(_run_bounded(document_id, title, chunk_texts), loop)


async def _run_bounded(document_id: str, title: str, chunk_texts: list[str]) -> None:
    sem = await _get_semaphore()
    async with sem:
        try:
            stats = await build_graph_for_document(document_id, title, chunk_texts)
            logger.info("[kg.build_service] xong document %s: %s", document_id, stats)
            _mark_status(document_id, GraphStatus.ready)
        except Exception as exc:  # noqa: BLE001 — thread nền, KHÔNG được để exception rơi mất
            logger.exception("[kg.build_service] lỗi cho document %s", document_id)
            _mark_status(document_id, GraphStatus.failed, error=str(exc)[:2000])


def _mark_status(document_id: str, status: GraphStatus, error: str | None = None) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return
        document.graph_status = status
        document.graph_error_message = error
        db.commit()
    finally:
        db.close()


def _ensure_neo4j_env() -> None:
    """LightRAG's Neo4JStorage đọc NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD trực tiếp từ
    os.environ (quy ước riêng của LightRAG, không đi qua constructor arg) — bridge từ
    `settings` (đọc .env qua pydantic-settings) sang os.environ để chạy đúng dù có hay
    không có docker-compose `env_file` export sẵn."""
    os.environ.setdefault("NEO4J_URI", settings.neo4j_uri)
    os.environ.setdefault("NEO4J_USERNAME", settings.neo4j_username)
    os.environ.setdefault("NEO4J_PASSWORD", settings.neo4j_password)


def _drop_summary() -> dict:
    by_reason: dict[str, int] = {}
    for item in graph_storage.DROP_LOG:
        key = item.get("reason") or ("bad_type" if item["kind"] == "node" else "?")
        by_reason[key] = by_reason.get(key, 0) + 1
    return by_reason


def _stamp_document_id(driver, document_id: str, title: str) -> None:
    """Gắn `document_id` thật lên MỌI node có `file_path == title` mà CHƯA từng được stamp
    — tránh đụng độ khi 2 document trùng title (Document.title không unique).
    graph_service.delete_by_document() ưu tiên xoá theo document_id, chỉ fallback file_path
    cho data cũ chưa stamp."""
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE n.file_path = $title AND n.document_id IS NULL "
            "SET n.document_id = $document_id",
            title=title, document_id=document_id,
        )


async def build_graph_for_document(document_id: str, title: str, chunk_texts: list[str]) -> dict:
    """Build KG cho 1 document. `chunk_texts` là plain list[str] (final_content đã
    contextual), KHÔNG phải ORM row — an toàn truyền qua thread khác.

    Best-effort SAU bước ainsert(): mỗi bước hậu xử lý lỗi bị log nhưng KHÔNG raise giữa
    chừng, giữ lại kết quả các bước trước đã ghi thành công. Lỗi ở chính ainsert() (bước
    ghi graph gốc) coi như build thất bại hoàn toàn — raise để `_run_in_thread` đánh dấu
    `graph_status=failed`."""
    _ensure_neo4j_env()
    full_text = "\n\n".join(chunk_texts)
    stats: dict = {}

    working_dir = os.path.join(_WORKING_DIR, document_id)
    os.makedirs(working_dir, exist_ok=True)
    rag = LightRAG(
        working_dir=working_dir,
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
    try:
        graph_storage.reset_drop_log()
        await rag.ainsert(full_text, ids=document_id, file_paths=title)
        stats["dropped"] = _drop_summary()
    finally:
        await rag.finalize_storages()

    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))
    try:
        try:
            stats["resolve_vanban"] = entity_resolution.resolve_vanban(driver)
            _stamp_document_id(driver, document_id, title)
        except Exception:  # noqa: BLE001
            logger.exception("[kg.build_service] resolve_vanban/stamp lỗi cho %s", document_id)

        try:
            stats["citations"] = citation_extractor.run_for_document(driver, title, full_text)
            stats["dedupe"] = {
                rel: entity_resolution.dedupe_parallel_relations(driver, rel)
                for rel in citation_extractor._CITATION_TYPES
            }
        except Exception:  # noqa: BLE001
            logger.exception("[kg.build_service] citation_extractor/dedupe lỗi cho %s", document_id)

        try:
            # Diacritics-normalized TRƯỚC embedding fuzzy: rẻ, deterministic, giảm số
            # candidate embedding phải xét — bắt được ca LLM extract KHÔNG dấu (vd "Mat
            # Khau" vs "Mật Khẩu") mà embedding trên bare name không đủ gần để tự gộp.
            stats["resolve_diacritics_khainiem"] = entity_resolution.resolve_diacritics_duplicates(driver, "KhaiNiem")
            stats["resolve_diacritics_giatriquydinh"] = entity_resolution.resolve_diacritics_duplicates(driver, "GiaTriQuyDinh")
            stats["resolve_khainiem"] = await entity_resolution.resolve_fuzzy_concepts(driver, "KhaiNiem")
            stats["resolve_giatriquydinh"] = await entity_resolution.resolve_fuzzy_concepts(driver, "GiaTriQuyDinh")
        except Exception:  # noqa: BLE001
            logger.exception("[kg.build_service] resolve_fuzzy_concepts lỗi cho %s", document_id)

        try:
            stats["link_provenance"] = concept_linker.link_provenance(driver, title)
            stats["link_concepts"] = await concept_linker.link_concepts(driver)
        except Exception:  # noqa: BLE001
            logger.exception("[kg.build_service] concept_linker lỗi cho %s", document_id)
    finally:
        driver.close()

    return stats
