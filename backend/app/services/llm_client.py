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

from openai import AsyncOpenAI, OpenAI

from app.config import settings

logger = logging.getLogger("llm_client")


class LLMError(RuntimeError):
    pass


def make_openai_client(async_client: bool = False) -> OpenAI | AsyncOpenAI:
    """Factory public tạo client OpenAI-compatible trỏ FPT (dùng chung cho app + eval).

    Mọi code ngoài llm_client (kể cả backend/eval) KHÔNG tự dựng openai.OpenAI —
    đây là điểm chặn duy nhất (LLM boundary).
    """
    if not settings.fpt_api_key:
        raise LLMError("FPT_API_KEY chưa được cấu hình (.env).")
    cls = AsyncOpenAI if async_client else OpenAI
    return cls(
        api_key=settings.fpt_api_key,
        base_url=settings.fpt_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def _client() -> OpenAI:
    client = make_openai_client()  # giữ nguyên hành vi cũ cho chat/vision/embed
    assert isinstance(client, OpenAI)
    return client


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


def _is_unsupported_param_error(exc: Exception) -> bool:
    """Model không hỗ trợ param (vd enable_thinking/chat_template_kwargs với model non-GLM)."""
    msg = str(exc).lower()
    return "unsupported parameter" in msg or "enable_thinking" in msg or "chat_template_kwargs" in msg


def _thinking_extra(disable_thinking: bool) -> dict | None:
    """extra_body để tắt reasoning của model GLM (chat_template_kwargs.enable_thinking=False)."""
    if not disable_thinking:
        return None
    return {"chat_template_kwargs": {"enable_thinking": False}}


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    cacheable_prefix_index: int | None = None,
    disable_thinking: bool | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
    tag: str = "chat",
) -> str:
    """Gọi chat completion non-stream, trả về text.

    cacheable_prefix_index: index của message (document prefix) để đánh dấu cache_control
    khi FPT_ENABLE_PROMPT_CACHE bật; nếu server từ chối field -> tự gửi lại không kèm.
    disable_thinking: tắt reasoning của GLM (mặc định lấy từ settings). Nếu model không
    hỗ trợ param -> tự gửi lại không kèm extra_body.
    """
    model = model or settings.fpt_chat_model
    if not model:
        raise LLMError("FPT_CHAT_MODEL chưa được cấu hình (.env).")
    if disable_thinking is None:
        disable_thinking = settings.fpt_disable_thinking

    use_cache = settings.fpt_enable_prompt_cache and cacheable_prefix_index is not None
    payload_messages = _with_cache_control(messages, cacheable_prefix_index) if use_cache else messages
    extra_body = _thinking_extra(disable_thinking)

    client = _client()

    def _call(msgs, eb):
        kwargs = dict(model=model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
        if eb:
            kwargs["extra_body"] = eb
        return client.chat.completions.create(**kwargs)

    try:
        resp = _call(payload_messages, extra_body)
    except Exception as exc:  # noqa: BLE001
        if use_cache and _is_cache_control_error(exc):
            logger.warning("cache_control không hỗ trợ, fallback gửi thường: %s", exc)
            try:
                resp = _call(messages, extra_body)
            except Exception as exc2:  # noqa: BLE001
                resp = _call(messages, None)
        elif _is_unsupported_param_error(exc):
            logger.warning("enable_thinking không hỗ trợ, fallback không extra_body: %s", exc)
            resp = _call(payload_messages, None)
        else:
            raise LLMError(f"chat() lỗi: {exc}") from exc

    _log_usage(tag, resp)
    return (resp.choices[0].message.content or "").strip()


def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    *,
    model: str | None = None,
    tool_choice: str = "auto",
    disable_thinking: bool | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = 1024,
    tag: str = "chat_tools",
):
    """Gọi chat completion có tool-calling (dùng cho ReAct subgraph của Retrieval Engine).

    Khác chat(): trả về nguyên message object của OpenAI SDK (có cả .content lẫn
    .tool_calls) thay vì chỉ text, vì phía gọi (LangGraph) cần biết model có yêu cầu
    gọi tool nào không, không chỉ nội dung trả lời.
    """
    model = model or settings.fpt_chat_model
    if not model:
        raise LLMError("FPT_CHAT_MODEL chưa được cấu hình (.env).")
    if disable_thinking is None:
        disable_thinking = settings.fpt_disable_thinking

    extra_body = _thinking_extra(disable_thinking)
    client = _client()

    def _call(eb):
        kwargs = dict(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if eb:
            kwargs["extra_body"] = eb
        return client.chat.completions.create(**kwargs)

    try:
        resp = _call(extra_body)
    except Exception as exc:  # noqa: BLE001
        if _is_unsupported_param_error(exc):
            logger.warning("enable_thinking không hỗ trợ (tools), fallback không extra_body: %s", exc)
            resp = _call(None)
        else:
            raise LLMError(f"chat_with_tools() lỗi: {exc}") from exc

    _log_usage(tag, resp)
    return resp.choices[0].message


def chat_stream(
    messages: list[dict],
    *,
    model: str | None = None,
    disable_thinking: bool | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
    tag: str = "chat_stream",
) -> Iterator[str]:
    """Gọi chat completion dạng stream, yield từng delta text (SSE của FPT)."""
    model = model or settings.fpt_chat_model
    if not model:
        raise LLMError("FPT_CHAT_MODEL chưa được cấu hình (.env).")
    if disable_thinking is None:
        disable_thinking = settings.fpt_disable_thinking

    client = _client()

    def _open_stream(eb):
        kwargs = dict(
            model=model, messages=messages, temperature=temperature,
            max_tokens=max_tokens, stream=True,
        )
        if eb:
            kwargs["extra_body"] = eb
        return client.chat.completions.create(**kwargs)

    try:
        try:
            stream = _open_stream(_thinking_extra(disable_thinking))
        except Exception as exc:  # noqa: BLE001
            if _is_unsupported_param_error(exc):
                logger.warning("enable_thinking không hỗ trợ (stream), fallback: %s", exc)
                stream = _open_stream(None)
            else:
                raise
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
