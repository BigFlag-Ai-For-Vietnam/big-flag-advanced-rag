"""Bước B — Chunking + Contextual Chunking (kỹ thuật Contextual Retrieval của Anthropic).

- SentenceSplitter tách full_document_text thành các chunk (raw_text).
- Với mỗi chunk, gọi LLM tạo "câu định vị" (contextual prefix), gửi toàn bộ document
  làm prefix (ưu tiên prompt caching nếu bật).
- final_content = title + câu định vị + raw_text  -> chuỗi sẽ được embed.
"""
from __future__ import annotations

import logging

from llama_index.core.node_parser import SentenceSplitter
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services import llm_client

logger = logging.getLogger("chunking_service")

# Prompt định vị — nguyên văn theo spec.
CONTEXT_PROMPT = (
    "Hãy viết 1-2 câu ngắn gọn để định vị đoạn này trong tài liệu. Câu trả lời BẮT BUỘC phải:\n"
    "1. Nêu rõ tên chủ thể/sản phẩm/dịch vụ/điều khoản cụ thể đang được đề cập "
    "(ví dụ: Thẻ tín dụng Sung Túc, Bảo hiểm sức khỏe Family Care)\n"
    "2. Nêu mục/phần/điều khoản cụ thể (nếu có)\n"
    "3. Tóm tắt nội dung chính.\n"
    "Chỉ trả về câu định vị bằng tiếng Việt, không giải thích gì thêm."
)


def split_text(text: str) -> list[str]:
    """Tách text thành các chunk theo cấu hình chunk_size / overlap / separator."""
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        paragraph_separator="\n\n",
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]


def build_final_content(title: str, contextual_prefix: str, raw_text: str) -> str:
    """final_content = title + câu định vị + \\n\\n + raw_text."""
    prefix = (contextual_prefix or "").strip()
    return f"{title}\n{prefix}\n\n{raw_text}".strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def _generate_context(full_document_text: str, chunk_text: str) -> str:
    """Gọi LLM sinh câu định vị cho 1 chunk.

    message[0] = document prefix (đánh dấu cacheable), message[1] = yêu cầu + chunk.
    """
    messages = [
        {
            "role": "user",
            "content": (
                "Đây là toàn bộ tài liệu:\n<document>\n"
                f"{full_document_text}\n</document>"
            ),
        },
        {
            "role": "user",
            "content": (
                "Đây là đoạn cần định vị trong tài liệu trên:\n<chunk>\n"
                f"{chunk_text}\n</chunk>\n\n" + CONTEXT_PROMPT
            ),
        },
    ]
    return llm_client.chat(
        messages,
        cacheable_prefix_index=0,  # document prefix dùng lại giữa các chunk
        disable_thinking=True,     # GLM reasoning sẽ ngốn hết token budget -> content rỗng
        temperature=0.0,
        max_tokens=settings.contextual_max_tokens,
        tag="contextual",
    )


def build_chunks(title: str, full_document_text: str) -> list[dict]:
    """Tạo list chunk dict: {chunk_index, raw_text, contextual_prefix, final_content}."""
    raw_chunks = split_text(full_document_text)
    out: list[dict] = []
    for idx, raw in enumerate(raw_chunks):
        try:
            context = _generate_context(full_document_text, raw)
        except Exception as exc:  # noqa: BLE001 — 1 chunk fail không nên chặn cả tài liệu
            logger.warning("Sinh contextual prefix lỗi cho chunk %s: %s", idx, exc)
            context = ""
        out.append(
            {
                "chunk_index": idx,
                "raw_text": raw,
                "contextual_prefix": context,
                "final_content": build_final_content(title, context, raw),
            }
        )
    return out
