"""Router documents: upload / list / detail / delete / reprocess / status."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.catalog_presets import resolve_focus_entities
from app.config import settings
from app.db import get_db
from app.models import Chunk, Document, DocumentStatus, GraphStatus
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    StatusResponse,
    SupersedeRequest,
    VersionChainItem,
    VersionChainResponse,
)
from app.services import graph_service, pipeline, qdrant_service, storage_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _parse_focus_entities(raw: str | None) -> list[str] | None:
    """focus_entities gửi từ form: chấp nhận JSON list, hoặc phân tách bằng xuống dòng/;/,."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    parts = [p.strip() for p in raw.replace(";", "\n").replace(",", "\n").split("\n")]
    return [p for p in parts if p] or None


def _chunk_count(db: Session, document_id: str) -> int:
    return db.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    ) or 0


def _lifecycle(doc: Document) -> str:
    """Suy ra trạng thái vòng đời để hiển thị: active | superseded | expired."""
    if doc.is_active:
        return "active"
    if doc.superseded_by_id:
        return "superseded"
    return "expired"


def _graph_status(doc: Document) -> GraphStatus:
    return GraphStatus(doc.graph_status or GraphStatus.not_built)


def _graph_eligible(doc: Document) -> bool:
    return bool(doc.category and doc.category in settings.kg_categories)


def _graph_build_enabled() -> bool:
    return settings.kg_enable_build and graph_service.is_configured()


def _apply_graph_state(output, doc: Document):
    output.graph_status = _graph_status(doc)
    output.graph_error_message = doc.graph_error_message
    output.graph_eligible = _graph_eligible(doc)
    output.graph_build_enabled = _graph_build_enabled()
    return output


def _to_summary(db: Session, doc: Document) -> DocumentSummary:
    summary = DocumentSummary.model_validate(doc)
    summary.chunk_count = _chunk_count(db, doc.id)
    summary.lifecycle = _lifecycle(doc)
    return _apply_graph_state(summary, doc)


def _to_status(db: Session, doc: Document) -> StatusResponse:
    return _apply_graph_state(
        StatusResponse(
            id=doc.id,
            status=doc.status,
            page_count=doc.page_count,
            chunk_count=_chunk_count(db, doc.id),
            error_message=doc.error_message,
            graph_status=_graph_status(doc),
            graph_error_message=doc.graph_error_message,
        ),
        doc,
    )


def _version_item(doc: Document) -> VersionChainItem:
    item = VersionChainItem.model_validate(doc)
    item.lifecycle = _lifecycle(doc)
    return item


@router.post("", response_model=DocumentSummary, status_code=201)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile,
    category: str | None = Form(None),
    focus_entities: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF.")

    document_id = str(uuid.uuid4())
    # file_path lưu STORAGE KEY (không phải path tuyệt đối) — storage_service phân giải
    # theo backend (local: {data_dir}/{key}, s3: object key trong bucket).
    file_key = storage_service.put_bytes(f"uploads/{document_id}.pdf", await file.read())

    # Chốt focus-entities cho catalog: custom (user nhập) > preset theo category > mặc định.
    resolved_entities = resolve_focus_entities(category, _parse_focus_entities(focus_entities))

    doc = Document(
        id=document_id,
        title=os.path.splitext(file.filename)[0],
        original_filename=file.filename,
        file_path=file_key,
        status=DocumentStatus.uploaded,
        category=category,
        focus_entities=resolved_entities,
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
    detail.lifecycle = _lifecycle(doc)
    return _apply_graph_state(detail, doc)


@router.get("/{document_id}/status", response_model=StatusResponse)
def get_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    return _to_status(db, doc)


@router.post("/{document_id}/reprocess", response_model=DocumentSummary)
def reprocess_document(
    document_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    if _graph_status(doc) == GraphStatus.building:
        raise HTTPException(
            status_code=409,
            detail="Knowledge Graph đang build; hãy chờ hoàn tất trước khi chạy lại toàn pipeline.",
        )
    doc.status = DocumentStatus.uploaded
    doc.error_message = None
    db.commit()
    background.add_task(pipeline.run_pipeline, document_id)
    return _to_summary(db, doc)


@router.post("/{document_id}/graph/rebuild", response_model=StatusResponse, status_code=202)
def rebuild_document_graph(document_id: str, db: Session = Depends(get_db)):
    """Build/retry/rebuild KG từ chunks hiện có, không chạy lại vector pipeline."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    if doc.status != DocumentStatus.indexed or _chunk_count(db, doc.id) == 0:
        raise HTTPException(
            status_code=409,
            detail="Document phải index xong và có chunks trước khi build Knowledge Graph.",
        )
    if not _graph_eligible(doc):
        raise HTTPException(
            status_code=422,
            detail=f"Category '{doc.category or ''}' không thuộc KG_CATEGORIES.",
        )
    if not _graph_build_enabled():
        raise HTTPException(
            status_code=503,
            detail="Knowledge Graph build đang tắt hoặc Neo4j credentials chưa đầy đủ.",
        )

    previous_status = _graph_status(doc)
    claimed = db.execute(
        update(Document)
        .where(
            Document.id == document_id,
            or_(
                Document.graph_status.is_(None),
                Document.graph_status != GraphStatus.building.value,
            ),
        )
        .values(graph_status=GraphStatus.building.value, graph_error_message=None)
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Knowledge Graph đang được build.")
    db.commit()
    db.refresh(doc)

    try:
        if previous_status in {GraphStatus.ready, GraphStatus.failed}:
            graph_service.delete_by_document(doc.id, doc.title, raise_on_error=True)
        from app.services.kg import build_service as kg_build_service  # lazy: import nặng

        kg_build_service.submit_graph_build(
            doc.id, doc.title, [chunk.final_content for chunk in doc.chunks]
        )
    except Exception as exc:  # noqa: BLE001
        doc.graph_status = GraphStatus.failed
        doc.graph_error_message = str(exc)[:2000]
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return _to_status(db, doc)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    if _graph_status(doc) == GraphStatus.building:
        raise HTTPException(
            status_code=409,
            detail="Knowledge Graph đang build; hãy chờ hoàn tất trước khi xóa document.",
        )
    if _graph_status(doc) != GraphStatus.not_built and graph_service.is_configured():
        try:
            graph_service.delete_by_document(doc.id, doc.title, raise_on_error=True)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    # Dọn Qdrant points trước, sau đó xoá DB (cascade xoá pages/chunks).
    qdrant_service.delete_by_document(document_id)
    # Xoá blob PDF gốc + ảnh page qua storage_service (best-effort, đã nuốt lỗi bên trong).
    if doc.file_path:
        storage_service.delete_prefix(doc.file_path)
    storage_service.delete_prefix(f"images/{document_id}/")
    db.delete(doc)
    db.commit()
    return None


# ----------------------------- versioning / hiệu lực -----------------------------

@router.post("/{document_id}/supersede", response_model=list[DocumentSummary])
def supersede_document(
    document_id: str,
    body: SupersedeRequest,
    db: Session = Depends(get_db),
):
    """Đánh dấu văn bản `document_id` bị THAY THẾ bởi `new_document_id`.

    Bản cũ: is_active=false, expiry_date=ngày hiệu lực bản mới, superseded_by_id=bản mới.
    Bản mới: is_active=true, supersedes_id=bản cũ. Cập nhật cờ trên Qdrant (không re-embed).
    """
    old = db.get(Document, document_id)
    if old is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy văn bản bị thay thế.")
    new = db.get(Document, body.new_document_id)
    if new is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy văn bản thay thế (new_document_id).")
    if old.id == new.id:
        raise HTTPException(status_code=400, detail="Văn bản không thể tự thay thế chính nó.")

    effective = body.effective_date or datetime.now(timezone.utc)
    old.is_active = False
    old.expiry_date = effective
    old.superseded_by_id = new.id
    if body.note:
        old.supersession_note = body.note
    new.is_active = True
    new.supersedes_id = old.id
    if new.effective_date is None:
        new.effective_date = effective
    db.commit()

    qdrant_service.set_active(old.id, False)
    qdrant_service.set_active(new.id, True)
    db.refresh(old)
    db.refresh(new)
    return [_to_summary(db, old), _to_summary(db, new)]


@router.post("/{document_id}/expire", response_model=DocumentSummary)
def expire_document(document_id: str, db: Session = Depends(get_db)):
    """Đánh dấu văn bản hết hiệu lực (không có bản thay thế)."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    doc.is_active = False
    doc.expiry_date = datetime.now(timezone.utc)
    db.commit()
    qdrant_service.set_active(doc.id, False)
    db.refresh(doc)
    return _to_summary(db, doc)


@router.post("/{document_id}/reactivate", response_model=DocumentSummary)
def reactivate_document(document_id: str, db: Session = Depends(get_db)):
    """Kích hoạt lại văn bản (reset demo): is_active=true, xoá expiry + liên kết bị thay thế."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    doc.is_active = True
    doc.expiry_date = None
    doc.superseded_by_id = None
    db.commit()
    qdrant_service.set_active(doc.id, True)
    db.refresh(doc)
    return _to_summary(db, doc)


@router.get("/{document_id}/versions", response_model=VersionChainResponse)
def get_version_chain(document_id: str, db: Session = Depends(get_db)):
    """Trả toàn bộ chuỗi phiên bản liên quan (đi theo cả supersedes_id lẫn superseded_by_id),
    sắp theo effective_date tăng dần (cũ -> mới) — cho UI timeline."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy document.")
    collected: dict[str, Document] = {}
    stack = [document_id]
    while stack:
        did = stack.pop()
        if did in collected:
            continue
        d = db.get(Document, did)
        if d is None:
            continue
        collected[did] = d
        for nid in (d.supersedes_id, d.superseded_by_id):
            if nid and nid not in collected:
                stack.append(nid)

    def _sort_key(d: Document) -> datetime:
        dt = d.effective_date or d.created_at
        # chuẩn hoá về aware-UTC: SQLite trả naive, còn giá trị vừa set qua API là aware
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    docs = sorted(collected.values(), key=_sort_key)
    return VersionChainResponse(items=[_version_item(d) for d in docs])
