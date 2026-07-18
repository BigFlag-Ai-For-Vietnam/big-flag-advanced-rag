"""Adapter LightRAG cho graph index dùng chung giữa các document.

Pipeline Qdrant hiện tại vẫn là nguồn retrieval chunk-level. Service này bổ sung
entity/relation graph từ toàn văn; danh sách facet user chọn lúc upload được chuyển
thành ``entity_types_guidance`` của LightRAG.

LightRAG dùng lock gắn với event loop. Backend v1 chạy pipeline sync trong
``BackgroundTasks``, vì vậy mỗi operation tạo + finalize instance trong cùng một
``asyncio.run`` và được serialize bằng process lock. Cách này phù hợp spike một
Uvicorn worker; khi chuyển sang nhiều worker cần một graph service/queue riêng.
"""
from __future__ import annotations

import asyncio
import logging
import re
import threading
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings
from app.services import llm_client

logger = logging.getLogger("lightrag_service")

_GRAPH_LOCK = threading.Lock()

_BASE_ENTITY_TYPES = (
    ("DOCUMENT", "Tài liệu, hợp đồng, quy tắc, điều khoản hoặc phụ lục đang được phân tích."),
    ("PRODUCT", "Sản phẩm tài chính, bảo hiểm, thẻ, gói quyền lợi hoặc dịch vụ có tên riêng."),
    ("ORGANIZATION", "Doanh nghiệp, ngân hàng, công ty bảo hiểm, cơ quan hoặc tổ chức có tên riêng."),
)


def _entity_type_key(label: str) -> str:
    """Đổi label tiếng Việt thành entity type ổn định, an toàn cho prompt/graph."""
    normalized = unicodedata.normalize("NFKD", label.replace("đ", "d").replace("Đ", "D"))
    ascii_label = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    key = re.sub(r"[^A-Za-z0-9]+", "_", ascii_label).strip("_").upper()
    return f"FACET_{key or 'OTHER'}"


def build_entity_types_guidance(focus_entities: list[str] | None) -> str:
    """Tạo guidance LightRAG: base types + đúng các facet đã chốt lúc upload.

    Facet là *loại* entity, không phải một entity chứa dữ liệu. Ví dụ facet
    ``Quyền lợi bảo hiểm`` dẫn LLM trích các node cụ thể như ``Trợ cấp mai táng``.
    """
    lines = [f"- {name}: {description}" for name, description in _BASE_ENTITY_TYPES]
    seen = {name for name, _ in _BASE_ENTITY_TYPES}

    for raw_label in focus_entities or []:
        label = str(raw_label).strip()
        if not label:
            continue
        base_key = _entity_type_key(label)
        key = base_key
        suffix = 2
        while key in seen:
            key = f"{base_key}_{suffix}"
            suffix += 1
        seen.add(key)
        lines.append(
            f'- {key}: Thực thể hoặc khái niệm cụ thể thuộc facet "{label}". '
            "Trích tên chuẩn từ tài liệu; không dùng chính tên facet làm entity nếu tài liệu "
            "không nhắc nó như một đối tượng cụ thể."
        )

    return "\n".join(lines)


def _working_dir() -> Path:
    configured = settings.lightrag_working_dir.strip()
    return Path(configured) if configured else Path(settings.data_dir) / "lightrag"


async def _llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> str:
    """Bridge async LightRAG -> LLM boundary OpenAI-compatible hiện có của app."""
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages or [])
    messages.append({"role": "user", "content": prompt})
    return await asyncio.to_thread(
        llm_client.chat,
        messages,
        max_tokens=settings.lightrag_llm_max_tokens,
        temperature=0.0,
        tag="lightrag_extract",
    )


async def _embedding_func(texts: list[str]) -> np.ndarray:
    vectors = await asyncio.to_thread(llm_client.embed, texts, tag="lightrag_embed")
    return np.asarray(vectors, dtype=np.float32)


def _build_rag(focus_entities: list[str] | None):
    """Import lazy để app vẫn báo lỗi cấu hình rõ ràng nếu image chưa rebuild."""
    try:
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
    except ImportError as exc:  # pragma: no cover - phụ thuộc môi trường runtime
        raise RuntimeError(
            "LIGHTRAG_ENABLED=true nhưng chưa cài lightrag-hku. "
            "Hãy rebuild backend image hoặc pip install -r backend/requirements.txt."
        ) from exc

    working_dir = _working_dir()
    working_dir.mkdir(parents=True, exist_ok=True)
    return LightRAG(
        working_dir=str(working_dir),
        workspace=settings.lightrag_workspace,
        llm_model_func=_llm_model_func,
        llm_model_name=settings.fpt_chat_model or "fpt-chat",
        llm_model_max_async=settings.lightrag_llm_max_async,
        embedding_func=EmbeddingFunc(
            embedding_dim=settings.embed_dim,
            max_token_size=8192,
            func=_embedding_func,
        ),
        embedding_func_max_async=settings.lightrag_embedding_max_async,
        chunk_token_size=settings.lightrag_chunk_token_size,
        chunk_overlap_token_size=settings.lightrag_chunk_overlap_token_size,
        entity_extraction_use_json=settings.lightrag_entity_extraction_use_json,
        addon_params={
            "language": settings.lightrag_language,
            "entity_types_guidance": build_entity_types_guidance(focus_entities),
        },
    )


async def _index_async(
    document_id: str,
    title: str,
    filename: str,
    full_text: str,
    focus_entities: list[str] | None,
) -> None:
    rag = _build_rag(focus_entities)
    await rag.initialize_storages()
    try:
        content = f"# Tài liệu: {title}\n\n{full_text.strip()}"
        await rag.ainsert(content, ids=document_id, file_paths=filename)
    finally:
        await rag.finalize_storages()


def index_document(
    document_id: str,
    title: str,
    filename: str,
    full_text: str,
    focus_entities: list[str] | None,
) -> bool:
    """Index một document vào LightRAG; trả False khi feature bị tắt."""
    if not settings.lightrag_enabled:
        logger.info("LightRAG tắt, bỏ qua graph index cho document %s", document_id)
        return False
    if not full_text.strip():
        raise ValueError("Không thể index LightRAG từ document rỗng.")

    with _GRAPH_LOCK:
        asyncio.run(_index_async(document_id, title, filename, full_text, focus_entities))
    logger.info("LightRAG graph index xong cho document %s", document_id)
    return True


async def _delete_async(document_id: str) -> None:
    rag = _build_rag(None)
    await rag.initialize_storages()
    try:
        await rag.adelete_by_doc_id(document_id)
    finally:
        await rag.finalize_storages()


def delete_document(document_id: str) -> bool:
    """Xóa provenance của document khỏi graph; no-op nếu chưa có graph storage."""
    if not _working_dir().exists():
        return False
    with _GRAPH_LOCK:
        asyncio.run(_delete_async(document_id))
    logger.info("Đã yêu cầu xóa document %s khỏi LightRAG", document_id)
    return True
