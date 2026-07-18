"""Nối LightRAG với FPT AI Marketplace (OpenAI-compatible).

LightRAG tự lái concurrency/retry của riêng nó và gọi thẳng `llm_model_func` /
`embedding_func` hàng chục/hàng trăm lần khi build graph — nên PoC này dùng thẳng
helper `openai_complete_if_cache` / `openai_embed` có sẵn của LightRAG (đọc
base_url/api_key/model từ `app.config.settings`, cùng nguồn config với backend thật)
thay vì đi qua `app/services/llm_client.py`.

Đây là ngoại lệ CÓ CHỦ ĐÍCH cho riêng PoC: `llm_client.py` là choke point cho app thật
(CLAUDE.md "LLM boundary"), nhưng PoC này chưa wire vào pipeline — không tự dựng
`openai.OpenAI()` thô, mà tái dùng model ID + api_key + base_url từ `settings` để không
lệch config với phần còn lại của repo.
"""
from __future__ import annotations

from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from app.config import settings


async def llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    **kwargs,
) -> str:
    # GLM-5.x là model reasoning: mặc định "nghĩ" trước khi trả lời, cực chậm (~phút/call)
    # khi LightRAG gọi hàng chục lần/document (extract + gleaning + continue-extraction cho
    # từng chunk). Tắt qua extra_body giống hệt `_thinking_extra()` trong app/services/llm_client.py
    # — nếu không tắt, PoC build 1 document 2 chunk có thể mất >15 phút thay vì ~1-2 phút.
    kwargs.setdefault("extra_body", {"chat_template_kwargs": {"enable_thinking": False}})
    return await openai_complete_if_cache(
        settings.fpt_chat_model,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        base_url=settings.fpt_base_url,
        api_key=settings.fpt_api_key,
        **kwargs,
    )


async def _embed(texts: list[str]):
    # openai_embed tự nó đã decorate bằng @wrap_embedding_func_with_attrs(embedding_dim=1536,
    # ...) (mặc định OpenAI text-embedding-3-small) — gọi THẲNG nó (không qua .func) sẽ bị
    # chính decorator đó ghi đè embedding_dim=1024 mình truyền, và validate output theo 1536
    # trong khi FPT Vietnamese_Embedding trả thật 1024 chiều -> luôn crash
    # "total elements cannot be evenly divided by expected dimension (1536)" dù cấu hình đúng.
    # `.func` lấy hàm gốc CHƯA decorate, để EmbeddingFunc ngoài (build_embedding_func, đúng
    # embedding_dim=1024) là lớp validate DUY NHẤT — tránh double-wrap (chính docstring của
    # EmbeddingFunc trong lightrag/utils.py cũng cảnh báo lỗi này).
    return await openai_embed.func(
        texts,
        model=settings.fpt_embed_model,
        base_url=settings.fpt_base_url,
        api_key=settings.fpt_api_key,
        embedding_dim=settings.embed_dim,
    )


def build_embedding_func() -> EmbeddingFunc:
    return EmbeddingFunc(embedding_dim=settings.embed_dim, func=_embed)
