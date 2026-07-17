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
