"""Test versioning / supersession (offline — SQLite in-memory, mock qdrant.set_active).

Gọi thẳng các hàm router (nhận db: Session) — không cần TestClient/mạng.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Document, DocumentStatus
from app.routers import documents as R
from app.schemas.document import SupersedeRequest


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
def _mock_qdrant(monkeypatch):
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(R.qdrant_service, "set_active", lambda did, active: calls.append((did, active)))
    return calls


def _mk(db, doc_id, title, active=True):
    doc = Document(
        id=doc_id, title=title, original_filename=f"{title}.pdf", file_path=f"uploads/{doc_id}.pdf",
        status=DocumentStatus.indexed, is_active=active,
    )
    db.add(doc)
    db.commit()
    return doc


def test_lifecycle_derivation(db):
    active = _mk(db, "a", "Bản còn hiệu lực")
    assert R._lifecycle(active) == "active"
    active.is_active = False
    active.superseded_by_id = "x"
    assert R._lifecycle(active) == "superseded"
    active.superseded_by_id = None
    assert R._lifecycle(active) == "expired"


def test_supersede_transitions(db, _mock_qdrant):
    old = _mk(db, "old", "QĐ 215 ATTT v1")
    new = _mk(db, "new", "QĐ 342 ATTT v2")

    result = R.supersede_document("old", SupersedeRequest(new_document_id="new", note="giữ Phụ lục 02"), db=db)

    assert old.is_active is False
    assert old.superseded_by_id == "new"
    assert old.expiry_date is not None
    assert old.supersession_note == "giữ Phụ lục 02"
    assert new.is_active is True
    assert new.supersedes_id == "old"
    assert new.effective_date is not None
    # cập nhật cả 2 chiều trên Qdrant (không re-embed)
    assert ("old", False) in _mock_qdrant
    assert ("new", True) in _mock_qdrant
    # trả về 2 summary với lifecycle đúng
    by_id = {s.id: s for s in result}
    assert by_id["old"].lifecycle == "superseded"
    assert by_id["new"].lifecycle == "active"


def test_supersede_self_rejected(db):
    _mk(db, "x", "Tự thay thế")
    with pytest.raises(Exception):
        R.supersede_document("x", SupersedeRequest(new_document_id="x"), db=db)


def test_expire_and_reactivate(db, _mock_qdrant):
    doc = _mk(db, "d", "Văn bản")
    R.expire_document("d", db=db)
    assert doc.is_active is False and doc.expiry_date is not None
    assert ("d", False) in _mock_qdrant

    R.reactivate_document("d", db=db)
    assert doc.is_active is True and doc.expiry_date is None and doc.superseded_by_id is None
    assert ("d", True) in _mock_qdrant


def test_version_chain_ordered(db, _mock_qdrant):
    _mk(db, "v1", "215")
    _mk(db, "v2", "342")
    R.supersede_document("v1", SupersedeRequest(new_document_id="v2"), db=db)

    chain = R.get_version_chain("v1", db=db)
    ids = [it.id for it in chain.items]
    # đi theo cả 2 chiều: chuỗi gồm cả v1 và v2, sắp theo effective_date (cũ -> mới)
    assert set(ids) == {"v1", "v2"}
    assert ids.index("v1") < ids.index("v2")
