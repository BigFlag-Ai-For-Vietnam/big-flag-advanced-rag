"""Pydantic schemas cho Playground RAG query."""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_index: int
    score: float
    final_content: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


class McpRetrieveRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ToolCallTrace(BaseModel):
    """1 lần react subgraph gọi tool trong lúc retrieval — phục vụ debug/quan sát."""

    tool: str
    args: dict
    hit_count: int


class RetrieveResult(BaseModel):
    """Kết quả gọi tool `retrieve` của Retrieval Engine — citations + trace quá trình."""

    citations: list[Citation]
    normalized_question: str
    rewritten_question: str
    tool_calls: list[ToolCallTrace]


class McpRetrieveConfig(BaseModel):
    """Trạng thái toggle hiện tại của Retrieval Engine — để FE hiển thị cùng kết quả,
    biết citation đang xem được sinh ra với normalize/rewrite/rerank bật/tắt thế nào."""

    normalize: bool
    rewrite: bool
    rerank: bool
    agent_max_steps: int


class McpRetrieveResponse(RetrieveResult):
    config: McpRetrieveConfig
