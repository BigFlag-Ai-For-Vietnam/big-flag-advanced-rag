"""Orchestrate pipeline A -> B -> C, cập nhật status document, xử lý lỗi.

Chạy nền bằng FastAPI BackgroundTasks (v1). Hướng nâng cấp v2: Celery.
"""
from __future__ import annotations

import logging
import uuid

from app.catalog_presets import resolve_focus_entities
from app.config import settings
from app.db import SessionLocal
from app.models import Chunk, Document, DocumentStatus, GraphStatus, Page
from app.services import (
    catalog_service,
    chunking_service,
    embedding_service,
    graph_service,
    parsing_service,
    qdrant_service,
    storage_service,
)

logger = logging.getLogger("pipeline")


def _set_status(db, document: Document, status: DocumentStatus, error: str | None = None) -> None:
    document.status = status
    if error is not None:
        document.error_message = error
    db.commit()


def run_pipeline(document_id: str) -> None:
    """Điểm vào cho BackgroundTasks. Tự mở session riêng (khác request session)."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            logger.error("Không tìm thấy document %s", document_id)
            return

        # Chạy lại: dọn dữ liệu cũ (pages/chunks + Qdrant points).
        _reset_document(db, document)

        # --- A. Parsing ---
        _set_status(db, document, DocumentStatus.parsing)
        pdf_bytes = storage_service.get_bytes(document.file_path)
        pages = parsing_service.parse_pdf(pdf_bytes, document.id)
        for p in pages:
            db.add(
                Page(
                    document_id=document.id,
                    page_number=p["page_number"],
                    parsed_text=p["parsed_text"],
                    image_ref=p["image_ref"],
                )
            )
        document.page_count = len(pages)
        full_text = parsing_service.join_pages(pages)
        _set_status(db, document, DocumentStatus.parsed)

        # Guard: nếu parse ra quá ít nội dung so với số trang -> nhiều khả năng VLM không
        # đọc được ảnh (model không hỗ trợ vision). Fail loud với thông báo hành động được.
        non_empty_pages = sum(1 for p in pages if (p.get("parsed_text") or "").strip())
        if not full_text.strip() or (len(pages) > 0 and non_empty_pages == 0):
            raise RuntimeError(
                "VLM parse rỗng cho tất cả trang. Kiểm tra FPT_VLM_MODEL có phải model "
                "VISION (hỗ trợ image_url) không — model chat/agentic thuần (vd GLM-5.x) "
                "sẽ bỏ qua ảnh và trả rỗng. Hoặc bật PARSE_TEXT_FALLBACK=true để dùng "
                "text-layer PDF."
            )
        used_fallback = sum(1 for p in pages if p.get("used_fallback"))
        if used_fallback:
            logger.warning(
                "%s/%s trang dùng text-layer fallback (VLM trả rỗng) — cân nhắc đổi "
                "FPT_VLM_MODEL sang model vision.",
                used_fallback,
                len(pages),
            )

        # --- B. Chunking + Contextual, rồi sinh CATALOG lean ---
        _set_status(db, document, DocumentStatus.chunking)
        focus_entities = document.focus_entities or resolve_focus_entities(document.category, None)

        # Chunk + contextual prefix TRƯỚC (catalog mặc định build từ chunk đã contextual).
        chunk_dicts = chunking_service.build_chunks(document.title, full_text)
        chunk_rows: list[Chunk] = []
        for cd in chunk_dicts:
            row = Chunk(
                document_id=document.id,
                chunk_index=cd["chunk_index"],
                raw_text=cd["raw_text"],
                contextual_prefix=cd["contextual_prefix"],
                final_content=cd["final_content"],
                qdrant_point_id=str(uuid.uuid4()),
                token_count=len(cd["final_content"].split()),
            )
            db.add(row)
            chunk_rows.append(row)
        db.commit()

        # --- Knowledge Graph build (Neo4j via LightRAG) — chạy NỀN, KHÔNG chặn catalog/Stage C.
        # Tách trạng thái riêng (graph_status) khỏi DocumentStatus: DocumentStatus.indexed vẫn
        # là tín hiệu DUY NHẤT "chunk-RAG dùng được", không phụ thuộc graph build xong hay chưa.
        if settings.kg_enable_build and document.category in settings.kg_categories:
            from app.services.kg import build_service as kg_build_service  # lazy: import nặng (lightrag)

            document.graph_status = GraphStatus.building
            db.commit()
            kg_build_service.submit_graph_build(
                document.id, document.title, [cd["final_content"] for cd in chunk_dicts]
            )

        # Catalog document-level (cây entities — chỉ TÊN mục, không có giá trị).
        # Nguồn: "chunks" (final_content đã contextual — mảnh self-contained nhờ câu định vị,
        # gán facet đúng kể cả khi section kéo dài qua nhiều trang / trang không header) hoặc
        # "pages" (parsed_text từng trang). Cấu hình qua CATALOG_SOURCE.
        if settings.catalog_source == "pages":
            catalog_units = [p.get("parsed_text") or "" for p in pages]
            unit_kind = "page"
        else:
            catalog_units = [cd["final_content"] for cd in chunk_dicts]
            unit_kind = "chunk"
        document.catalog = catalog_service.generate_catalog(
            document.title,
            catalog_units,
            focus_entities,
            unit_kind=unit_kind,
            full_text_fallback=full_text,
        )
        db.commit()

        # --- C. Indexing ---
        _set_status(db, document, DocumentStatus.indexing)
        qdrant_service.ensure_collection()
        vectors = embedding_service.embed_texts([r.final_content for r in chunk_rows])
        points = [
            {
                "id": row.qdrant_point_id,
                "vector": vec,
                "payload": {
                    "document_id": document.id,
                    "chunk_id": row.id,
                    "chunk_index": row.chunk_index,
                    "title": document.title,
                    "final_content": row.final_content,
                },
            }
            for row, vec in zip(chunk_rows, vectors)
        ]
        qdrant_service.upsert_chunks(points)

        _set_status(db, document, DocumentStatus.indexed)
        logger.info("Pipeline xong cho document %s (%s chunks)", document.id, len(chunk_rows))

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline lỗi cho document %s", document_id)
        try:
            document = db.get(Document, document_id)
            if document is not None:
                _set_status(db, document, DocumentStatus.failed, error=str(exc)[:2000])
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


def _reset_document(db, document: Document) -> None:
    """Xoá pages/chunks cũ + Qdrant points + graph nodes để reprocess sạch."""
    if document.status == DocumentStatus.uploaded and not document.pages and not document.chunks:
        return
    qdrant_service.delete_by_document(document.id)
    if document.graph_status == GraphStatus.building:
        # Graph-build cũ còn đang chạy nền (thread khác, ngoài vòng đời request này) — xoá
        # giữa chừng có thể corrupt state đang ghi dở. Bỏ qua lần này; graph_status sẽ được
        # reset đúng ở lần reprocess SAU, khi build cũ đã xong (ready|failed).
        logger.warning("Document %s đang graph-build dở — bỏ qua xoá graph lần này", document.id)
    else:
        # document.title không unique (2 lần upload cùng tên file) -> graph_service ưu tiên
        # xoá theo document_id (đã stamp bởi build_service), chỉ fallback title cho data cũ
        # chưa được stamp — tránh xoá nhầm graph của 1 document khác trùng title.
        graph_service.delete_by_document(document.id, document.title)
        document.graph_status = None
        document.graph_error_message = None
    db.query(Page).filter(Page.document_id == document.id).delete()
    db.query(Chunk).filter(Chunk.document_id == document.id).delete()
    document.error_message = None
    document.page_count = None
    document.catalog = None
    db.commit()
