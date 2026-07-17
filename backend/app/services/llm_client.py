"""Client gọi FPT AI Marketplace (OpenAI-compatible): chat / stream / embed / vision.

Điểm quan trọng:
- Base URL + api_key trỏ tới FPT (https://mkp-api.fptcloud.com).
- Prompt caching CHƯA được FPT xác nhận: hàm chat() nhận cờ cacheable prefix,
  nếu bật thì đính cache_control kiểu Anthropic/OpenAI, nếu API từ chối field
  thì tự động fallback gửi lại không kèm cache_control. Chạy đúng trong cả 2 trường hợp.
- Log token usage cho mỗi call.
"""
from __future__ import annotations

import base64
import logging
from typing import Iterator

from openai import OpenAI

from app.config import settings

logger = logging.getLogger("llm_client")


class LLMError(RuntimeError):
    pass


def _client() -> OpenAI:
    if not settings.fpt_api_key:
        raise LLMError("FPT_API_KEY chưa được cấu hình (.env).")
    return OpenAI(
        api_key=settings.fpt_api_key,
        base_url=settings.fpt_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def _log_usage(tag: str, response) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    # cached tokens (nếu API trả) nằm trong prompt_tokens_details.cached_tokens
    cached = None
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", None)
    logger.info(
        "[%s] usage prompt=%s completion=%s total=%s cached=%s",
        tag,
        getattr(usage, "prompt_tokens", "?"),
        getattr(usage, "completion_tokens", "?"),
        getattr(usage, "total_tokens", "?"),
        cached,
    )


def _is_cache_control_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "cache_control" in msg or "cache-control" in msg


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    cacheable_prefix_index: int | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
    tag: str = "chat",
) -> str:
    """Gọi chat completion non-stream, trả về text.

    cacheable_prefix_index: index của message (thường là system/document prefix) cần
    đánh dấu cache_control khi FPT_ENABLE_PROMPT_CACHE bật. Nếu server từ chối field,
    tự động thử lại không kèm cache_control.
    """
    model = model or settings.fpt_chat_model
    if not model:
        raise LLMError("FPT_CHAT_MODEL chưa được cấu hình (.env).")

    use_cache = settings.fpt_enable_prompt_cache and cacheable_prefix_index is not None
    payload_messages = _with_cache_control(messages, cacheable_prefix_index) if use_cache else messages

    client = _client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        if use_cache and _is_cache_control_error(exc):
            logger.warning("cache_control không được hỗ trợ, fallback gửi thường: %s", exc)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise LLMError(f"chat() lỗi: {exc}") from exc

    _log_usage(tag, resp)
    return (resp.choices[0].message.content or "").strip()


def chat_stream(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
    tag: str = "chat_stream",
) -> Iterator[str]:
    """Gọi chat completion dạng stream, yield từng delta text (SSE của FPT)."""
    model = model or settings.fpt_chat_model
    if not model:
        raise LLMError("FPT_CHAT_MODEL chưa được cấu hình (.env).")

    client = _client()
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"chat_stream() lỗi: {exc}") from exc


def vision(image_bytes: bytes, prompt: str, *, model: str | None = None, tag: str = "vision") -> str:
    """Gửi 1 ảnh (PNG bytes) + prompt tới model VLM theo chuẩn OpenAI vision."""
    model = model or settings.fpt_vlm_model
    if not model:
        raise LLMError("FPT_VLM_MODEL chưa được cấu hình (.env).")

    b64 = base64.b64encode(image_bytes).decode("ascii")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            ],
        }
    ]
    client = _client()
    try:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.0)
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"vision() lỗi: {exc}") from exc

    _log_usage(tag, resp)
    return (resp.choices[0].message.content or "").strip()


def embed(texts: list[str], *, model: str | None = None, tag: str = "embed") -> list[list[float]]:
    """Embed danh sách text (batch) qua FPT embeddings endpoint."""
    model = model or settings.fpt_embed_model
    if not model:
        raise LLMError("FPT_EMBED_MODEL chưa được cấu hình (.env).")
    if not texts:
        return []

    client = _client()
    try:
        resp = client.embeddings.create(model=model, input=texts)
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"embed() lỗi: {exc}") from exc

    _log_usage(tag, resp)
    # Sắp xếp theo index để đảm bảo đúng thứ tự.
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]


def _with_cache_control(messages: list[dict], index: int) -> list[dict]:
    """Trả về bản copy messages với cache_control đính vào message ở vị trí index.

    Chuyển content string -> dạng array block để gắn cache_control kiểu Anthropic/OpenAI.
    """
    import copy

    out = copy.deepcopy(messages)
    if not (0 <= index < len(out)):
        return out
    msg = out[index]
    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = [
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    elif isinstance(content, list) and content:
        # đính vào block cuối cùng của prefix
        content[-1]["cache_control"] = {"type": "ephemeral"}
    return out
