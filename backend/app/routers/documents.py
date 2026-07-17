"""Router documents: upload / list / detail / delete / reprocess / status."""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Chunk, Document, DocumentStatus
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    StatusResponse,
)
from app.services import pipeline, qdrant_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _chunk_count(db: Session, document_id: str) -> int:
    return db.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    ) or 0


def _to_summary(db: Session, doc: Document) -> DocumentSummary:
    summary = DocumentSummary.model_validate(doc)
    summary.chunk_count = _chunk_count(db, doc.id)
    return summary


@router.post("", response_model=DocumentSummary, status_code=201)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF.")

    document_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{document_id}.pdf")
    with open(file_path, "wb") as fh:
        fh.write(await file.read())

    doc = Document(
        id=document_id,
        title=os.path.splitext(file.filename)[0],
        original_filename=file.filename,
        file_path=file_path,
        status=DocumentStatus.uploaded,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(pipeline.run_pipeline, document_id)
    return _to_summary(db, doc)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = db.scalar(select(func.count(Document.id))) or 0
    rows = db.scalars(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentListResponse(
        items=[_to_summary(db, d) for d in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    detail = DocumentDetail.model_validate(doc)
    detail.chunk_count = len(doc.chunks)
    return detail


@router.get("/{document_id}/status", response_model=StatusResponse)
def get_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    return StatusResponse(
        id=doc.id,
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=_chunk_count(db, doc.id),
        error_message=doc.error_message,
    )


@router.post("/{document_id}/reprocess", response_model=DocumentSummary)
def reprocess_document(
    document_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    doc.status = DocumentStatus.uploaded
    doc.error_message = None
    db.commit()
    background.add_task(pipeline.run_pipeline, document_id)
    return _to_summary(db, doc)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    # Dọn Qdrant points trước, sau đó xoá DB (cascade xoá pages/chunks).
    qdrant_service.delete_by_document(document_id)
    # Xoá file PDF gốc (best-effort).
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError:
        pass
    db.delete(doc)
    db.commit()
    return None
