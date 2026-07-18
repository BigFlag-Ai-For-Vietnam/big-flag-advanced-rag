"""Model documents + enum trạng thái pipeline."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsing = "parsing"
    parsed = "parsed"
    chunking = "chunking"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(512))
    # STORAGE KEY của PDF gốc (vd "uploads/{id}.pdf"), phân giải bởi storage_service
    # theo backend (local: {data_dir}/{key}; s3: object key trong bucket) — không phải path tuyệt đối.
    file_path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.uploaded,
        index=True,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- Catalog metadata (cây entities "lean": chỉ tên mục, không có data) ---
    # category preset user chọn lúc upload (vd "the_tin_dung", "bao_hiem")
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # danh sách facet-entities LLM cần focus khi sinh catalog (preset đã resolve/customize)
    focus_entities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # catalog: {"tree": [{"name": "...", "children": [{"name": "...", "children": []}, ...]}, ...]}
    # — cây phân cấp, chỉ tên mục, không kèm giá trị
    catalog: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    pages: Mapped[list["Page"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Page.page_number",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Chunk.chunk_index",
    )


from app.models.page import Page  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402
