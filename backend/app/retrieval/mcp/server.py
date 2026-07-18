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
from app.schemas.playground import RetrieveResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("retrieval.mcp.server")

mcp = FastMCP("retrieval-engine", host="0.0.0.0", port=8100)


@mcp.tool()
def retrieve(question: str, top_k: int = 5) -> RetrieveResult:
    """Tìm các đoạn tài liệu liên quan nhất tới câu hỏi (điều khoản, quyền lợi, phí, sản
    phẩm/dịch vụ ngân hàng đã index). KHÔNG sinh câu trả lời; caller tự dùng citation
    để trả lời câu hỏi.

    Trả về:
    - citations: danh sách (document_id, title, chunk_index, score, final_content)
    - graph_facts: quan hệ/thực thể lấy từ knowledge graph (Neo4j) — KHÔNG phải trích dẫn
      nguyên văn, dùng để suy luận quan hệ/xung đột/thay thế giữa văn bản (rỗng nếu
      RETRIEVAL_ENABLE_GRAPH=false hoặc Neo4j chưa cấu hình).
    - normalized_question / rewritten_question: câu hỏi sau từng bước xử lý
    - tool_calls: danh sách tool đã gọi trong lúc retrieval (tool, args, hit_count)
      — phục vụ debug/quan sát pipeline, không ảnh hưởng tới việc dùng citations.

    Trả về Pydantic model (không phải dict trần) để FastMCP sinh được outputSchema —
    dict trần khiến SDK không tạo structuredContent, chỉ trả text JSON trong content.
    """
    logger.info("[mcp.retrieve] question=%r top_k=%s", question, top_k)
    result = engine.retrieve(question, top_k)
    logger.info(
        "[mcp.retrieve] trả về %s citation(s), %s graph fact(s)",
        len(result["citations"]), len(result["graph_facts"]),
    )
    return RetrieveResult(
        citations=result["citations"],
        graph_facts=result["graph_facts"],
        normalized_question=result["normalized_question"],
        rewritten_question=result["rewritten_question"],
        tool_calls=result["tool_calls"],
        subgoals=result["subgoals"],
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
