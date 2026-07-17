"""Tool cho react subgraph: query_vector_store (thật) + query_graph_knowledge (stub).

Mỗi tool log input/output gọn qua logger.info để quan sát được từng bước ReAct loop
làm gì (không log nguyên final_content dài, tránh spam log).
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.services import embedding_service, qdrant_service

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
    hits = qdrant_service.search(query_vector, top_k)
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
def query_graph_knowledge(query: str) -> list[dict]:
    """Tra cứu tri thức dạng quan hệ/thực thể (graph) giữa các sản phẩm/điều khoản/dịch vụ.

    CHƯA có dữ liệu graph thật (Ingestion chưa có bước sinh graph) — hiện luôn trả về
    rỗng. Vẫn có thể gọi thử nếu câu hỏi có vẻ cần quan hệ giữa nhiều thực thể.
    """
    logger.info("[query_graph_knowledge] input query=%r (stub — chờ Ingestion sinh graph)", query)
    results: list[dict] = []
    logger.info("[query_graph_knowledge] output hits=0 (stub)")
    return results
