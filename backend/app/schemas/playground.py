"""Pydantic schemas cho Playground RAG query."""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False
    # dùng ReAct agent (catalog-aware) hay one-shot QA đơn giản
    use_agent: bool = True


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_index: int
    score: float
    final_content: str


class CatalogInfo(BaseModel):
    """Catalog document-level đính kèm câu trả lời (để UI hiển thị bản đồ mục lục)."""
    document_id: str
    title: str
    catalog: dict


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    catalogs: list[CatalogInfo] = []


# --- Retrieval Engine (LangGraph + MCP) ---

class McpRetrieveRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ToolCallTrace(BaseModel):
    """1 lần gather gọi retrieve cho 1 sub-goal — phục vụ debug/quan sát."""

    tool: str
    args: dict
    hit_count: int


class SubgoalCoverage(BaseModel):
    """Coverage của 1 sub-goal sau agentic planning — để nêu rõ đã đủ / còn thiếu gì."""

    description: str
    query: str
    satisfied: bool
    note: str = ""
    evidence_count: int = 0


class RetrieveResult(BaseModel):
    """Kết quả gọi tool `retrieve` của Retrieval Engine — citations + trace + coverage."""

    citations: list[Citation]
    normalized_question: str
    rewritten_question: str
    tool_calls: list[ToolCallTrace]
    subgoals: list[SubgoalCoverage] = []


class McpRetrieveConfig(BaseModel):
    """Trạng thái toggle hiện tại của Retrieval Engine — để FE hiển thị cùng kết quả,
    biết citation đang xem được sinh ra với normalize/rewrite/rerank bật/tắt thế nào."""

    normalize: bool
    rewrite: bool
    rerank: bool
    agent_max_steps: int


class McpRetrieveResponse(RetrieveResult):
    config: McpRetrieveConfig


class ShowcaseCompareRequest(BaseModel):
    """Một input duy nhất được gửi đồng thời vào advanced và raw RAG."""

    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
