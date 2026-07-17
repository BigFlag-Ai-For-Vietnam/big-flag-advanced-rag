"""MCP client — kết nối tới Retrieval Engine (server riêng, app/retrieval/mcp/server.py)
qua streamable-http. Giữ 1 ClientSession sống theo vòng đời app (mở ở FastAPI startup,
đóng ở shutdown — xem app/main.py) — routers/playground.py gọi qua đây, KHÔNG import
thẳng app.retrieval.engine. Đây là caller thứ 2 của cùng 1 service, cùng cách Cursor/
Claude Code gọi — không có đường tắt nào khác.
"""
from __future__ import annotations

import logging
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings
from app.schemas.playground import Citation

logger = logging.getLogger("retrieval.mcp.client")

_stack: AsyncExitStack | None = None
_session: ClientSession | None = None


async def connect() -> None:
    global _stack, _session
    if _session is not None:
        return
    _stack = AsyncExitStack()
    read, write, _ = await _stack.enter_async_context(streamablehttp_client(settings.retrieval_mcp_url))
    _session = await _stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()
    logger.info("[mcp.client] đã kết nối tới Retrieval Engine tại %s", settings.retrieval_mcp_url)


async def close() -> None:
    global _stack, _session
    if _stack is not None:
        await _stack.aclose()
    _stack = None
    _session = None


async def retrieve(question: str, top_k: int = 5) -> list[Citation]:
    """Gọi đúng 1 lần tool `retrieve` của Retrieval Engine, trả về citations."""
    if _session is None:
        raise RuntimeError("MCP client chưa kết nối — connect() phải chạy ở FastAPI startup trước.")
    result = await _session.call_tool("retrieve", {"question": question, "top_k": top_k})
    if result.isError:
        raise RuntimeError(f"Retrieval Engine trả lỗi: {result.content}")
    citations_raw = (result.structuredContent or {}).get("result", [])
    return [Citation(**c) for c in citations_raw]
