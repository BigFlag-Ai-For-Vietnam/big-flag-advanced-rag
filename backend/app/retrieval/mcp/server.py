"""MCP server — expose Retrieval Engine qua đúng 1 tool: retrieve(question, top_k).

Chạy như process/image riêng (backend/Dockerfile.mcp + service retrieval-mcp trong
docker-compose.yml), transport streamable-http. Đây là bề mặt DUY NHẤT ra ngoài của
Retrieval Engine — mọi caller (kể cả backend FastAPI của chính app, xem Bước 5) đều
gọi qua tool này, không import thẳng app.retrieval.engine.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from app.retrieval import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("retrieval.mcp.server")

mcp = FastMCP("retrieval-engine", host="0.0.0.0", port=8100)


@mcp.tool()
def retrieve(question: str, top_k: int = 5) -> list[dict]:
    """Tìm các đoạn tài liệu liên quan nhất tới câu hỏi (điều khoản, quyền lợi, phí, sản
    phẩm/dịch vụ ngân hàng đã index). Trả về danh sách citation (document_id, title,
    chunk_index, score, final_content) — KHÔNG sinh câu trả lời; caller tự dùng citation
    này để trả lời câu hỏi.
    """
    logger.info("[mcp.retrieve] question=%r top_k=%s", question, top_k)
    citations = engine.retrieve(question, top_k)
    logger.info("[mcp.retrieve] trả về %s citation(s)", len(citations))
    return [c.model_dump() for c in citations]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
