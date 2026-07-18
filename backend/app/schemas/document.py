"""Pydantic schemas cho documents / pages / chunks."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.document import DocumentStatus, GraphStatus


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
    # Knowledge Graph chạy độc lập với vector pipeline.
    graph_status: GraphStatus = GraphStatus.not_built
    graph_error_message: str | None = None
    graph_eligible: bool = False
    graph_build_enabled: bool = False
    # --- versioning / hiệu lực ---
    doc_no: str | None = None
    version_label: str | None = None
    effective_date: datetime | None = None
    expiry_date: datetime | None = None
    is_active: bool = True
    supersedes_id: str | None = None
    superseded_by_id: str | None = None
    supersession_note: str | None = None
    # trạng thái vòng đời suy ra: active | superseded | expired (đặt trong _to_summary)
    lifecycle: str = "active"
    created_at: datetime
    updated_at: datetime

    @field_validator("graph_status", mode="before")
    @classmethod
    def _normalize_graph_status(cls, value):
        return value or GraphStatus.not_built


class DocumentDetail(DocumentSummary):
    focus_entities: list[str] | None = None
    catalog: dict | None = None
    pages: list[PageOut] = []
    chunks: list[ChunkOut] = []


class SupersedeRequest(BaseModel):
    """Đánh dấu văn bản hiện tại (id trên path) bị thay thế bởi new_document_id."""
    new_document_id: str
    note: str | None = None          # ghi chú thay thế (vd giữ Phụ lục 02)
    effective_date: datetime | None = None  # ngày hiệu lực bản mới (mặc định: now)


class VersionChainItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    doc_no: str | None = None
    version_label: str | None = None
    effective_date: datetime | None = None
    expiry_date: datetime | None = None
    is_active: bool = True
    lifecycle: str = "active"


class VersionChainResponse(BaseModel):
    items: list[VersionChainItem]   # sắp theo effective_date tăng dần (cũ -> mới)


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
    graph_status: GraphStatus = GraphStatus.not_built
    graph_error_message: str | None = None
    graph_eligible: bool = False
    graph_build_enabled: bool = False
