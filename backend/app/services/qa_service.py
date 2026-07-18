"""Dịch vụ QA dùng chung: retrieval + dựng prompt + gọi answer (router + eval CLI)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document
from app.schemas.playground import CatalogInfo, Citation, GraphFact, SubgoalCoverage
from app.services import catalog_service, embedding_service, llm_client, qdrant_service

SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)

ADVANCED_SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
    "CATALOG là bản đồ mục lục của tài liệu (chỉ tên mục, không có giá trị) — dùng để trả "
    "lời ĐẦY ĐỦ, đặc biệt câu hỏi liệt kê (đối chiếu catalog xem đã đủ mục chưa). "
    "TRI THỨC ĐỒ THỊ (nếu có) là quan hệ giữa văn bản/khái niệm (căn cứ/thay thế/tham chiếu/"
    "ưu tiên hơn, hoặc nhiều giá trị khác nhau cho cùng 1 khái niệm) — dùng để SUY LUẬN quan "
    "hệ/xung đột/thay thế xuyên văn bản, KHÔNG phải trích dẫn nguyên văn; trích dẫn [số] vẫn "
    "chỉ trỏ vào NGỮ CẢNH (đoạn văn bản), không trỏ vào tri thức đồ thị. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là không tìm thấy trong tài liệu. "
    "Trả lời bằng tiếng Việt, trích dẫn nguồn theo dạng [số] khi phù hợp."
)


def retrieve(question: str, top_k: int) -> list[Citation]:
    query_vec = embedding_service.embed_query(question)
    hits = qdrant_service.search(query_vec, top_k)
    return [
        Citation(
            document_id=h["payload"].get("document_id", ""),
            title=h["payload"].get("title", ""),
            chunk_index=h["payload"].get("chunk_index", -1),
            score=h["score"],
            final_content=h["payload"].get("final_content", ""),
        )
        for h in hits
    ]


def build_messages(question: str, citations: list[Citation]) -> list[dict]:
    context_blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(context_blocks) if context_blocks else "(không có ngữ cảnh)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {question}"},
    ]


def fetch_catalogs(db: Session, citations: list[Citation]) -> list[CatalogInfo]:
    """Lấy catalog document-level cho các document xuất hiện trong citations."""
    doc_ids: list[str] = []
    for citation in citations:
        if citation.document_id and citation.document_id not in doc_ids:
            doc_ids.append(citation.document_id)

    result: list[CatalogInfo] = []
    for document_id in doc_ids:
        document = db.get(Document, document_id)
        if settings.retrieval_exclude_inactive and document and not document.is_active:
            continue
        if document and document.catalog and document.catalog.get("tree"):
            result.append(
                CatalogInfo(document_id=document.id, title=document.title, catalog=document.catalog)
            )
    return result


def build_advanced_messages(
    question: str,
    citations: list[Citation],
    catalogs: list[CatalogInfo],
    subgoals: list[SubgoalCoverage],
    graph_facts: list[GraphFact] | None = None,
) -> list[dict]:
    """Prompt advanced: text evidence + catalog + graph facts + coverage còn thiếu."""
    blocks = [
        f"[{i + 1}] (Tài liệu: {c.title}, đoạn #{c.chunk_index})\n{c.final_content}"
        for i, c in enumerate(citations)
    ]
    context = "\n\n".join(blocks) if blocks else "(không có ngữ cảnh)"
    catalog_text = "\n\n".join(
        catalog_service.format_catalog_text(c.title, c.catalog) for c in catalogs
    ).strip()
    graph_text = _format_graph_facts(graph_facts or [])
    missing = [
        f"- {s.description}: {s.note or 'chưa đủ bằng chứng'}"
        for s in subgoals
        if not s.satisfied
    ]

    parts = [f"NGỮ CẢNH:\n{context}"]
    if catalog_text:
        parts.append(f"CATALOG:\n{catalog_text}")
    if graph_text:
        parts.append(
            "TRI THỨC ĐỒ THỊ (quan hệ giữa văn bản/khái niệm — KHÔNG phải trích dẫn nguyên văn):\n"
            + graph_text
        )
    if missing:
        parts.append(
            "PHẦN CÒN THIẾU BẰNG CHỨNG (nêu rõ trong câu trả lời, KHÔNG bịa):\n"
            + "\n".join(missing)
        )
    parts.append(f"CÂU HỎI: {question}")
    return [
        {"role": "system", "content": ADVANCED_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def _format_graph_facts(graph_facts: list[GraphFact]) -> str:
    lines: list[str] = []
    for fact in graph_facts:
        properties = f" ({fact.properties})" if fact.properties else ""
        source = (
            f" [nguồn: {fact.source_document_title}]" if fact.source_document_title else ""
        )
        lines.append(
            f"- {fact.source_entity} --{fact.relation}--> "
            f"{fact.target_entity}{properties}{source}"
        )
    return "\n".join(lines)


def answer(question: str, top_k: int) -> tuple[str, list[Citation]]:
    """Trả về (câu trả lời non-stream, citations) — cùng tham số mặc định với playground."""
    citations = retrieve(question, top_k)
    messages = build_messages(question, citations)
    text = llm_client.chat(messages, temperature=0.2, max_tokens=1024, tag="qa")
    return text, citations
