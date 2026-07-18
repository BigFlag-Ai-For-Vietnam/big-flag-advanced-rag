"""Pydantic schemas cho documents / pages / chunks."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_number: int
    parsed_text: str | None = None


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chunk_index: int
    raw_text: str
    contextual_prefix: str | None = None
    final_content: str
    qdrant_point_id: str | None = None
    token_count: int | None = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_filename: str
    status: DocumentStatus
    category: str | None = None
    page_count: int | None = None
    chunk_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    focus_entities: list[str] | None = None
    catalog: dict | None = None
    pages: list[PageOut] = []
    chunks: list[ChunkOut] = []


class CatalogPreset(BaseModel):
    key: str
    label: str
    entities: list[str]


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int


class StatusResponse(BaseModel):
    id: str
    status: DocumentStatus
    page_count: int | None = None
    chunk_count: int = 0
    error_message: str | None = None
