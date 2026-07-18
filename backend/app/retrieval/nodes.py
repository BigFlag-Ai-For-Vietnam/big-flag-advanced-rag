"""Node deterministic của outer graph: normalize/rewrite chạy trước react subgraph
(đúng 1 lần, không loop), rerank chạy sau (đúng 1 lần, luôn chạy — không phải tool
cho LLM tự chọn gọi).

Gọi llm_client.chat() trực tiếp, không qua BaseChatModel — các hàm ở đây không cần
interface LangChain vì không phải một phần của react subgraph (không tool-calling).

Mỗi hàm tự check flag bật/tắt của mình (RETRIEVAL_ENABLE_*) và log input/output để
quan sát ảnh hưởng của từng bước.
"""
from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import AIMessage, ToolMessage

from app.config import settings
from app.schemas.playground import Citation
from app.services import llm_client

logger = logging.getLogger("retrieval.nodes")

REWRITE_PROMPT = (
    "Bạn hỗ trợ chuẩn hoá câu hỏi cho hệ thống tìm kiếm tài liệu ngân hàng (điều khoản, "
    "quyền lợi, phí, sản phẩm/dịch vụ). Nếu câu hỏi thiếu tên sản phẩm/dịch vụ cụ thể, "
    "giữ nguyên — KHÔNG bịa tên sản phẩm không có trong câu hỏi gốc. Viết lại câu hỏi rõ "
    "ràng, đầy đủ ý hơn, phù hợp để tìm kiếm ngữ nghĩa. CHỈ trả về câu hỏi đã viết lại, "
    "không giải thích gì thêm."
)


def normalize(question: str) -> str:
    """Dọn dẹp câu hỏi (strip/whitespace) — thuần Python, không gọi LLM."""
    if not settings.retrieval_enable_normalize:
        logger.info("[normalize] tắt (RETRIEVAL_ENABLE_NORMALIZE=false) — passthrough input=%r", question)
        return question
    result = re.sub(r"\s+", " ", question).strip()
    logger.info("[normalize] input=%r output=%r", question, result)
    return result


def rewrite(question: str) -> str:
    """1 lần gọi LLM để làm rõ/chuẩn hoá câu hỏi trước khi vào react subgraph."""
    if not settings.retrieval_enable_rewrite:
        logger.info("[rewrite] tắt (RETRIEVAL_ENABLE_REWRITE=false) — passthrough input=%r", question)
        return question
    result = llm_client.chat(
        [
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=200,
        tag="retrieval_rewrite",
    ).strip() or question
    logger.info("[rewrite] input=%r output=%r", question, result)
    return result


def _parse_tool_message(msg: ToolMessage) -> list[dict]:
    content = msg.content
    if not isinstance(content, str):
        return content if isinstance(content, list) else []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def build_trace(messages: list) -> list[dict]:
    """Trace các lần react subgraph gọi tool: tool name, args, số hit trả về.

    Ghép AIMessage.tool_calls (tool nào, args gì) với ToolMessage tương ứng (theo
    tool_call_id) để biết mỗi lần gọi trả về bao nhiêu hit — phục vụ debug UI (MCP
    Playground) chứ không dùng để tính citations (đó là việc của rerank()).
    """
    tool_call_meta: dict[str, dict] = {}
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls or []:
                tool_call_meta[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}

    trace: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id in tool_call_meta:
            meta = tool_call_meta[msg.tool_call_id]
            hits = _parse_tool_message(msg)
            trace.append({"tool": meta["tool"], "args": meta["args"], "hit_count": len(hits)})
    return trace


def rerank(messages: list, top_k: int) -> list[Citation]:
    """Gom kết quả mọi lần gọi tool trong react subgraph, dedupe, sort, cắt top_k.

    Luôn chạy đúng 1 lần sau khi react subgraph dừng — không phải tool cho LLM tự
    quyết định có gọi hay không (rerank là bước lọc bắt buộc, không phải tuỳ chọn).
    """
    candidates: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            for item in _parse_tool_message(msg):
                # chỉ hit dạng chunk (có chunk_id) mới thành citation; kết quả query_catalog
                # (mục lục, không có chunk_id/final_content) chỉ để agent tham khảo, không trích.
                if isinstance(item, dict) and item.get("chunk_id"):
                    candidates.append(item)

    deduped: dict[str, dict] = {}
    for c in candidates:
        key = c.get("chunk_id") or f"{c.get('document_id')}:{c.get('chunk_index')}"
        if key not in deduped:
            deduped[key] = c
    ordered = list(deduped.values())

    if settings.retrieval_enable_rerank:
        ordered.sort(key=lambda c: c.get("score", 0.0), reverse=True)
    else:
        logger.info("[rerank] tắt (RETRIEVAL_ENABLE_RERANK=false) — chỉ dedupe, giữ thứ tự xuất hiện")

    top = ordered[:top_k]
    logger.info(
        "[rerank] candidates=%s deduped=%s output=%s chunk_ids=%s",
        len(candidates),
        len(ordered),
        len(top),
        [c.get("chunk_id") for c in top],
    )
    return [
        Citation(
            document_id=c.get("document_id", ""),
            title=c.get("title", ""),
            chunk_index=c.get("chunk_index", -1),
            score=c.get("score", 0.0),
            final_content=c.get("final_content", ""),
        )
        for c in top
    ]
