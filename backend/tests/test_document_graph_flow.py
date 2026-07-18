"""Dual-status ingest + manual KG build tests (offline)."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base
from app.models import Chunk, Document, DocumentStatus, GraphStatus
from app.routers import documents as R
from app.services.kg import build_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def graph_config(monkeypatch):
    monkeypatch.setattr(settings, "kg_enable_build", True)
    monkeypatch.setattr(settings, "kg_categories", ["van_ban_tuan_thu"])
    monkeypatch.setattr(settings, "neo4j_uri", "bolt://fake:7687")
    monkeypatch.setattr(settings, "neo4j_username", "neo4j")
    monkeypatch.setattr(settings, "neo4j_password", "secret")


def _doc(db, *, category="van_ban_tuan_thu", graph_status=GraphStatus.not_built):
    document = Document(
        id="doc-1",
        title="Văn bản",
        original_filename="van-ban.pdf",
        file_path="uploads/doc-1.pdf",
        status=DocumentStatus.indexed,
        category=category,
        graph_status=graph_status,
    )
    document.chunks.append(
        Chunk(
            id="chunk-1",
            chunk_index=0,
            raw_text="Nội dung",
            final_content="Văn bản quy định nội dung",
            qdrant_point_id="point-1",
        )
    )
    db.add(document)
    db.commit()
    return document


def test_summary_exposes_independent_graph_state(db):
    document = _doc(db)
    result = R._to_summary(db, document)
    assert result.status == DocumentStatus.indexed
    assert result.graph_status == GraphStatus.not_built
    assert result.graph_eligible is True
    assert result.graph_build_enabled is True


def test_manual_graph_build_uses_existing_chunks(db, monkeypatch):
    document = _doc(db)
    submitted = []
    monkeypatch.setattr(
        build_service,
        "submit_graph_build",
        lambda doc_id, title, chunks: submitted.append((doc_id, title, chunks)),
    )

    result = R.rebuild_document_graph(document.id, db=db)

    assert result.graph_status == GraphStatus.building
    assert submitted == [(document.id, document.title, ["Văn bản quy định nội dung"])]


def test_manual_rebuild_deletes_old_graph_first(db, monkeypatch):
    document = _doc(db, graph_status=GraphStatus.ready)
    calls = []
    monkeypatch.setattr(
        R.graph_service,
        "delete_by_document",
        lambda doc_id, title, raise_on_error=False: calls.append((doc_id, title, raise_on_error)) or True,
    )
    monkeypatch.setattr(build_service, "submit_graph_build", lambda *args: calls.append("submit"))

    R.rebuild_document_graph(document.id, db=db)

    assert calls == [(document.id, document.title, True), "submit"]


def test_build_rejects_ineligible_and_duplicate(db, monkeypatch):
    ineligible = _doc(db, category="quy_trinh")
    with pytest.raises(HTTPException) as exc:
        R.rebuild_document_graph(ineligible.id, db=db)
    assert exc.value.status_code == 422

    ineligible.category = "van_ban_tuan_thu"
    ineligible.graph_status = GraphStatus.building
    db.commit()
    monkeypatch.setattr(build_service, "submit_graph_build", lambda *args: None)
    with pytest.raises(HTTPException) as exc:
        R.rebuild_document_graph(ineligible.id, db=db)
    assert exc.value.status_code == 409


def test_submit_failure_is_retryable_graph_failure(db, monkeypatch):
    document = _doc(db)
    monkeypatch.setattr(
        build_service, "submit_graph_build", lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    with pytest.raises(HTTPException) as exc:
        R.rebuild_document_graph(document.id, db=db)

    db.refresh(document)
    assert exc.value.status_code == 503
    assert document.status == DocumentStatus.indexed
    assert document.graph_status == GraphStatus.failed
    assert "boom" in document.graph_error_message
