"""Nguồn dữ liệu sinh testset: gom chunk đã index từ SQLite và dựng KnowledgeGraph ragas."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus


class DocumentNotIndexedError(RuntimeError):
    """Tài liệu được yêu cầu nhưng chưa ở trạng thái indexed."""

    def __init__(self, document_id: str, status: DocumentStatus) -> None:
        self.document_id = document_id
        self.status = status
        super().__init__(
            f"Tài liệu {document_id} chưa sẵn sàng để sinh testset "
            f"(trạng thái hiện tại: {status.value}, yêu cầu: {DocumentStatus.indexed.value})"
        )


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str        # Chunk.id (uuid str)
    document_id: str     # Chunk.document_id
    title: str           # Document.title
    chunk_index: int     # Chunk.chunk_index
    final_content: str   # Chunk.final_content (title + prefix + raw_text)


def collect_chunks(
    session: Session, document_ids: Sequence[str] | None = None
) -> list[ChunkRecord]:
    """document_ids=None (--all): mọi document indexed. Danh sách id tường minh:
    id không tồn tại -> ValueError; status != indexed -> DocumentNotIndexedError."""
    if document_ids is None:
        documents = list(session.scalars(select(Document).where(Document.status == DocumentStatus.indexed)))
    else:
        documents = []
        for doc_id in document_ids:
            doc = session.get(Document, doc_id)
            if doc is None:
                raise ValueError(f"Không tìm thấy tài liệu: {doc_id}")
            if doc.status != DocumentStatus.indexed:
                raise DocumentNotIndexedError(doc_id, doc.status)
            documents.append(doc)

    records: list[ChunkRecord] = []
    for doc in documents:
        for chunk in doc.chunks:  # relationship đã order_by="Chunk.chunk_index"
            records.append(ChunkRecord(
                chunk_id=chunk.id,
                document_id=doc.id,
                title=doc.title,
                chunk_index=chunk.chunk_index,
                final_content=chunk.final_content,
            ))
    return records


def build_kg(
    chunks: Sequence[ChunkRecord],
    transforms: Any | None = None,
    llm: Any | None = None,
    embedding_model: Any | None = None,
) -> Any:  # ragas.testset.graph.KnowledgeGraph
    from ragas.testset.graph import KnowledgeGraph, Node, NodeType
    from ragas.testset.transforms import apply_transforms, default_transforms_for_prechunked

    kg = KnowledgeGraph(nodes=[
        Node(
            type=NodeType.CHUNK,
            properties={
                "page_content": rec.final_content,
                "document_metadata": {
                    "document_id": rec.document_id,
                    "chunk_id": rec.chunk_id,
                    "title": rec.title,
                    "chunk_index": rec.chunk_index,
                },
            },
        )
        for rec in chunks
    ])

    if transforms is None:
        if llm is None or embedding_model is None:
            raise ValueError(
                "Cần truyền llm + embedding_model để dựng transforms mặc định "
                "(hoặc tự truyền transforms) — không dùng fallback ngầm của ragas."
            )
        transforms = default_transforms_for_prechunked(llm=llm, embedding_model=embedding_model)

    apply_transforms(kg, transforms)
    return kg


def build_and_log_kg(
    chunks: Sequence[ChunkRecord],
    out_path: Path,
    transforms: Any | None = None,
    llm: Any | None = None,
    embedding_model: Any | None = None,
) -> Any:
    """build_kg + kg.save(str(out_path)) + mlflow.log_artifact(str(out_path)).
    Yêu cầu caller đã mở mlflow run (CLI generate lo việc đó)."""
    import mlflow

    kg = build_kg(chunks, transforms=transforms, llm=llm, embedding_model=embedding_model)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kg.save(str(out_path))
    mlflow.log_artifact(str(out_path))
    return kg
