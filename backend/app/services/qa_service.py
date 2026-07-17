"""Dịch vụ QA dùng chung: retrieval + dựng prompt + gọi answer (router + eval CLI)."""
from __future__ import annotations

from app.schemas.playground import Citation
from app.services import embedding_service, llm_client, qdrant_service

SYSTEM_PROMPT = (
    "Bạn là trợ lý hỏi–đáp dựa trên tài liệu. Chỉ trả lời dựa vào NGỮ CẢNH được cung cấp. "
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


def answer(question: str, top_k: int) -> tuple[str, list[Citation]]:
    """Trả về (câu trả lời non-stream, citations) — cùng tham số mặc định với playground."""
    citations = retrieve(question, top_k)
    messages = build_messages(question, citations)
    text = llm_client.chat(messages, temperature=0.2, max_tokens=1024, tag="qa")
    return text, citations
