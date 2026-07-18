"""Model documents + enum trạng thái pipeline."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Text
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


class GraphStatus(str, enum.Enum):
    """Trạng thái build knowledge graph (Neo4j) — tách biệt khỏi DocumentStatus vì graph-build
    chạy nền song song với Qdrant indexing: DocumentStatus.indexed phải là tín hiệu DUY NHẤT
    "chunk-RAG dùng được", không phụ thuộc graph đã xong hay chưa."""

    not_built = "not_built"
    building = "building"
    ready = "ready"
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
    # category preset user chọn lúc upload (vd "van_ban_tuan_thu", "quy_trinh")
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # danh sách facet-entities LLM cần focus khi sinh catalog (preset đã resolve/customize)
    focus_entities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # catalog: {"tree": [{"name": "...", "children": [{"name": "...", "children": []}, ...]}, ...]}
    # — cây phân cấp, chỉ tên mục, không kèm giá trị
    catalog: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # --- Versioning / hiệu lực (theo dõi văn bản hết hiệu lực, thay thế) ---
    # số hiệu văn bản (vd "342/2024/QĐ-DDB") — business key gom nhóm các phiên bản cùng một văn bản
    doc_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    version_label: Mapped[str | None] = mapped_column(String(32), nullable=True)  # vd "v2.0"
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # còn hiệu lực hay không — khóa retrieval theo cột này (hết hiệu lực bị loại khỏi tìm kiếm)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # soft-FK (String, KHÔNG ràng buộc — hợp migration nhẹ + self-FK SQLite ALTER không hỗ trợ)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)      # bản này thay thế ai
    superseded_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)   # ai thay thế bản này
    supersession_note: Mapped[str | None] = mapped_column(Text, nullable=True)        # vd "giữ hiệu lực Phụ lục 02"
    # --- Knowledge Graph build (Neo4j via LightRAG) — độc lập với `status` ở trên ---
    graph_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=GraphStatus.not_built
    )
    graph_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
