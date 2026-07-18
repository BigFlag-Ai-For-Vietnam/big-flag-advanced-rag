"""Test hybrid retrieval (offline): fuse() thuần hàm + BM25 corpus loại văn bản hết hiệu lực."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Chunk, Document, DocumentStatus
from app.retrieval import hybrid
from app.retrieval.hybrid import fuse


def _h(cid, score, doc="d1", idx=0, content="x", title="T"):
    return {"chunk_id": cid, "document_id": doc, "chunk_index": idx, "title": title, "final_content": content, "score": score}


def test_fuse_normalizes_and_weights():
    dense = [_h("c1", 0.9), _h("c2", 0.6)]
    bm25 = [_h("c3", 10.0), _h("c1", 5.0)]
    out = fuse(dense, bm25, top_k=3, alpha=0.5)
    ids = [o["chunk_id"] for o in out]
    # c1 có ở cả 2 nguồn -> điểm fuse cao nhất
    assert ids[0] == "c1"
    # tất cả điểm trong [0,1]
    assert all(0.0 <= o["score"] <= 1.0 for o in out)


def test_fuse_bm25_surfaces_keyword_only_hit():
    # chunk bảng phí chỉ BM25 bắt được (dense không trả về) vẫn lọt vào kết quả
    dense = [_h("cA", 0.8)]
    bm25 = [_h("cFee", 12.0, content="Từ 51 đến 60 tuổi Gói 2 2.445.000")]
    out = fuse(dense, bm25, top_k=2, alpha=0.5)
    assert "cFee" in [o["chunk_id"] for o in out]


def test_fuse_alpha_prioritizes_dense():
    dense = [_h("cD", 1.0)]
    bm25 = [_h("cB", 1.0)]
    out = fuse(dense, bm25, top_k=2, alpha=0.9)  # thiên dense
    assert out[0]["chunk_id"] == "cD"


def test_fuse_empty_sources():
    assert fuse([], [], top_k=5) == []


# ---------------------------------------------------------------- BM25 corpus + versioning

@pytest.fixture()
def seeded_hybrid(monkeypatch):
    """SQLite in-memory: văn bản còn hiệu lực (chunk 'alpha') + hết hiệu lực (chunk 'beta'),
    kèm vài văn bản 'filler' để keyword là từ thiểu số (BM25 IDF > 0 như corpus thật)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, future=True)
    db = Factory()
    rows = [("act", True, "alpha"), ("dead", False, "beta")]
    rows += [(f"f{i}", True, "tongquan") for i in range(5)]  # filler (không chứa alpha/beta)
    for did, active, kw in rows:
        db.add(Document(id=did, title=f"doc {did}", original_filename=f"{did}.pdf",
                        file_path=f"uploads/{did}.pdf", status=DocumentStatus.indexed, is_active=active))
        db.add(Chunk(id=f"c_{did}", document_id=did, chunk_index=0,
                     raw_text=f"noi dung {kw}", final_content=f"noi dung {kw} chuong muc"))
    db.commit()
    db.close()

    monkeypatch.setattr(hybrid, "SessionLocal", Factory)
    hybrid._cache.update(count=-1, bm25=None, chunks=[])  # buộc rebuild corpus
    yield Factory
    hybrid._cache.update(count=-1, bm25=None, chunks=[])  # dọn cho test khác


def test_bm25_excludes_inactive_document(seeded_hybrid, monkeypatch):
    monkeypatch.setattr(hybrid.settings, "retrieval_exclude_inactive", True)
    # 'beta' chỉ có trong văn bản đã hết hiệu lực -> không được trả về
    assert hybrid.bm25_search("beta", 5) == []
    # 'alpha' của văn bản còn hiệu lực -> vẫn tìm thấy
    got = hybrid.bm25_search("alpha", 5)
    assert [h["document_id"] for h in got] == ["act"]


def test_bm25_includes_inactive_when_toggle_off(seeded_hybrid, monkeypatch):
    monkeypatch.setattr(hybrid.settings, "retrieval_exclude_inactive", False)
    got = hybrid.bm25_search("beta", 5)
    assert [h["document_id"] for h in got] == ["dead"]
