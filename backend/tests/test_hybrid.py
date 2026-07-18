"""Test fuse() của hybrid retrieval (offline, thuần hàm — không đụng SQLite/Qdrant)."""
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
