"""Tool cho react subgraph: query_vector_store (chunk) + query_graph_knowledge (Neo4j).

Mỗi tool log input/output gọn qua logger.info để quan sát được từng bước ReAct loop
làm gì (không log nguyên final_content dài, tránh spam log).
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.config import settings
from app.services import embedding_service, graph_service, qdrant_service

logger = logging.getLogger("retrieval.tools")


@tool
def query_vector_store(query: str, top_k: int = 5) -> list[dict]:
    """Tìm các đoạn văn bản liên quan nhất trong kho vector (Qdrant) theo ngữ nghĩa.

    Dùng khi cần tra cứu nội dung cụ thể trong tài liệu đã index (điều khoản, quyền
    lợi, phí, sản phẩm/dịch vụ ngân hàng...). query nên là câu hỏi/cụm từ rõ ràng,
    càng cụ thể càng dễ khớp (nêu tên sản phẩm/dịch vụ nếu biết).
    """
    logger.info("[query_vector_store] input query=%r top_k=%s", query, top_k)
    query_vector = embedding_service.embed_query(query)
    hits = qdrant_service.search(query_vector, top_k, active_only=settings.retrieval_exclude_inactive)
    results = [
        {
            "chunk_id": h["payload"].get("chunk_id", ""),
            "document_id": h["payload"].get("document_id", ""),
            "title": h["payload"].get("title", ""),
            "chunk_index": h["payload"].get("chunk_index", -1),
            "score": h["score"],
            "final_content": h["payload"].get("final_content", ""),
        }
        for h in hits
    ]
    top_score = results[0]["score"] if results else None
    logger.info(
        "[query_vector_store] output hits=%s top_score=%s chunk_ids=%s",
        len(results),
        top_score,
        [r["chunk_id"] for r in results],
    )
    return results


@tool
def query_catalog(query: str, top_k: int = 5) -> list[dict]:
    """Xem CATALOG (mục lục theo facet — chỉ TÊN mục, KHÔNG có giá trị cụ thể) của các tài
    liệu liên quan tới `query`.

    Dùng để biết tổng thể tài liệu có những mục nào / bao nhiêu mục — đặc biệt cho câu hỏi
    liệt kê hoặc tổng hợp (vd "có những loại phí nào"): đối chiếu catalog để biết cần lấy đủ
    bao nhiêu mục, rồi dùng query_vector_store lấy dữ liệu cụ thể từng mục. Catalog KHÔNG
    chứa số liệu — muốn giá trị phải gọi query_vector_store.
    """
    logger.info("[query_catalog] input query=%r top_k=%s", query, top_k)
    # import trong hàm: chỉ khi tool được gọi mới đụng tới DB (MCP service mount SQLite riêng)
    from app.db import SessionLocal
    from app.models import Document
    from app.services.catalog_service import format_catalog_text

    hits = qdrant_service.search(
        embedding_service.embed_query(query), top_k, active_only=settings.retrieval_exclude_inactive
    )
    doc_ids: list[str] = []
    for h in hits:
        did = h["payload"].get("document_id")
        if did and did not in doc_ids:
            doc_ids.append(did)

    results: list[dict] = []
    db = SessionLocal()
    try:
        for did in doc_ids:
            doc = db.get(Document, did)
            # bỏ qua văn bản đã hết hiệu lực khi loại-bỏ đang bật
            if settings.retrieval_exclude_inactive and doc and not doc.is_active:
                continue
            if doc and doc.catalog and doc.catalog.get("tree"):
                results.append(
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "outline": format_catalog_text(doc.title, doc.catalog),
                    }
                )
    finally:
        db.close()
    logger.info("[query_catalog] output docs=%s", [r["document_id"] for r in results])
    return results


@tool
def query_graph_knowledge(query: str) -> list[dict]:
    """Tra cứu tri thức dạng quan hệ/thực thể (graph) giữa các văn bản/khái niệm/giá trị quy
    định — dùng để phát hiện quan hệ căn cứ/thay thế/tham chiếu giữa văn bản, hoặc để lộ ra
    nhiều giá trị khác nhau (có thể mâu thuẫn) cho CÙNG 1 khái niệm kèm văn bản nguồn.
    KHÔNG phải trích dẫn nguyên văn — dùng để suy luận quan hệ/xung đột/thay thế, không dùng
    để trả lời trực tiếp câu hỏi tra cứu nội dung cụ thể (đó là việc của query_vector_store).
    """
    logger.info("[query_graph_knowledge] input query=%r", query)
    if not settings.retrieval_enable_graph or not graph_service.is_configured():
        logger.info("[query_graph_knowledge] output hits=0 (graph tắt hoặc Neo4j chưa cấu hình)")
        return []
    results = graph_service.concept_matches(query, settings.retrieval_graph_concept_top_k)
    logger.info("[query_graph_knowledge] output hits=%s", len(results))
    return results
