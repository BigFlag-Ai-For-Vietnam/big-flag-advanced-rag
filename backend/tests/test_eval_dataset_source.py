"""Test nguồn dữ liệu sinh testset (FR-1) — offline, SQLite in-memory."""
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from eval.dataset_source import DocumentNotIndexedError, build_and_log_kg, collect_chunks


@pytest.fixture
def session():
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        yield s


def _make_document(session, status, title, n_chunks):
    doc = Document(title=title, original_filename=f"{title}.pdf", file_path=f"uploads/{title}.pdf", status=status)
    session.add(doc)
    session.flush()
    for i in range(n_chunks):
        session.add(Chunk(
            document_id=doc.id,
            chunk_index=i,
            raw_text=f"raw {i}",
            final_content=f"final content {title} #{i}",
        ))
    session.commit()
    return doc


def test_collect_chunks_only_indexed(session):
    indexed_doc = _make_document(session, DocumentStatus.indexed, "Indexed Doc", 3)
    _make_document(session, DocumentStatus.parsing, "Parsing Doc", 1)

    records = collect_chunks(session, None)

    assert len(records) == 3
    assert [r.chunk_index for r in records] == [0, 1, 2]
    for r in records:
        assert r.document_id == indexed_doc.id
        assert r.title == "Indexed Doc"
        assert r.final_content == f"final content Indexed Doc #{r.chunk_index}"


def test_non_indexed_document_rejected(session):
    parsing_doc = _make_document(session, DocumentStatus.parsing, "Parsing Doc", 1)

    with pytest.raises(DocumentNotIndexedError) as exc_info:
        collect_chunks(session, [parsing_doc.id])

    assert "parsing" in str(exc_info.value)


def test_kg_built_and_persisted(session, tmp_path, monkeypatch):
    pytest.importorskip("ragas")
    from ragas.testset.graph import NodeType

    indexed_doc = _make_document(session, DocumentStatus.indexed, "Indexed Doc", 3)
    records = collect_chunks(session, [indexed_doc.id])

    calls = []
    fake_mlflow = types.ModuleType("mlflow")
    fake_mlflow.log_artifact = lambda p: calls.append(p)
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    out_path = tmp_path / "kg.json"
    kg = build_and_log_kg(records, out_path, transforms=[])

    assert len(kg.nodes) == 3
    for node, rec in zip(kg.nodes, records):
        assert node.type == NodeType.CHUNK
        assert node.properties["page_content"] == rec.final_content
    assert out_path.exists()
    assert calls == [str(out_path)]
