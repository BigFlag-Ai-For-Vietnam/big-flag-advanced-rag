"""Test graph_service (offline) — monkeypatch graph_service._driver() trả fake driver với
.session().run(...) trả record giả. Chỉ test phần shaping/dedup/gating Python thuần, không
cố mock toàn bộ Cypher session (không có Neo4j thật trong CI)."""
from app.config import settings
from app.services import graph_service


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows


class _FakeSession:
    """Trả rows theo thứ tự gọi run() — mỗi test tự khai queue đúng thứ tự query thật gọi.
    Queue được CHIA SẺ giữa các session() (concept_matches mở session mới cho mỗi round-trip)."""

    def __init__(self, queue):
        self._queue = queue  # tham chiếu chung, KHÔNG copy — pop() phải ảnh hưởng qua các session

    def run(self, query, **params):
        return _FakeResult(self._queue.pop(0))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeDriver:
    def __init__(self, queue):
        self._queue = list(queue)

    def session(self):
        return _FakeSession(self._queue)


def _configure_neo4j(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_uri", "bolt://fake:7687")
    monkeypatch.setattr(settings, "neo4j_username", "neo4j")
    monkeypatch.setattr(settings, "neo4j_password", "secret")


def test_is_configured_false_without_password(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_password", "")
    assert graph_service.is_configured() is False


def test_citation_neighbors_empty_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_password", "")
    assert graph_service.citation_neighbors(["Thông tư X"]) == []


def test_citation_neighbors_shapes_facts(monkeypatch):
    _configure_neo4j(monkeypatch)
    rows = [
        {
            "source": "Thông tư 09/2024/TT-NHNN", "source_type": "VanBan",
            "target": "Quyết định 342/2020/QĐ-DDB", "target_type": "VanBan",
            "relation": "THAY_THE",
            "rel_props": {"ontology_relation": "THAY_THE", "partial": True, "giu_hieu_luc": "Phụ lục 02"},
            "file_path": "TT09_2024.pdf",
        }
    ]
    monkeypatch.setattr(graph_service, "_driver", lambda: _FakeDriver([rows]))

    facts = graph_service.citation_neighbors(["TT09_2024.pdf"])

    assert len(facts) == 1
    fact = facts[0]
    assert fact["fact_id"] == "Thông tư 09/2024/TT-NHNN|THAY_THE|Quyết định 342/2020/QĐ-DDB"
    assert fact["relation"] == "THAY_THE"
    assert fact["properties"] == {"partial": True, "giu_hieu_luc": "Phụ lục 02"}
    assert fact["strategy"] == "citation_neighbor"
    assert fact["source_document_title"] == "TT09_2024.pdf"


def test_citation_neighbors_swallows_neo4j_error(monkeypatch):
    _configure_neo4j(monkeypatch)

    class _BrokenDriver:
        def session(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(graph_service, "_driver", lambda: _BrokenDriver())
    assert graph_service.citation_neighbors(["x"]) == []


def test_concept_matches_empty_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_password", "")
    assert graph_service.concept_matches("mật khẩu bao nhiêu ký tự") == []


def test_concept_matches_bundles_value_and_source(monkeypatch):
    _configure_neo4j(monkeypatch)
    concepts = [{"name": "Mật khẩu", "desc": "Độ dài tối thiểu mật khẩu đăng nhập"}]
    bundle_rows = [
        {
            "concept": "Mật khẩu", "value": "08 ký tự", "value_type": "GiaTriQuyDinh",
            "ap_props": {"ontology_relation": "AP_DUNG_CHO", "source": "concept_linker.concept"},
            "vanban": "Thông tư 09/2024/TT-NHNN", "file_path": "TT09_2024.pdf",
            "qd_props": {"ontology_relation": "QUY_DINH", "source": "concept_linker.provenance"},
        },
        {
            "concept": "Mật khẩu", "value": "12 ký tự", "value_type": "GiaTriQuyDinh",
            "ap_props": {"ontology_relation": "AP_DUNG_CHO"},
            "vanban": "Quyết định 342/2020/QĐ-DDB", "file_path": "QD342_2020.pdf",
            "qd_props": {"ontology_relation": "QUY_DINH"},
        },
    ]
    driver = _FakeDriver([concepts, bundle_rows])
    monkeypatch.setattr(graph_service, "_driver", lambda: driver)

    facts = graph_service.concept_matches("mật khẩu bao nhiêu ký tự")

    relations = {(f["source_entity"], f["relation"], f["target_entity"]) for f in facts}
    assert ("08 ký tự", "AP_DUNG_CHO", "Mật khẩu") in relations
    assert ("Thông tư 09/2024/TT-NHNN", "QUY_DINH", "08 ký tự") in relations
    assert ("12 ký tự", "AP_DUNG_CHO", "Mật khẩu") in relations
    assert ("Quyết định 342/2020/QĐ-DDB", "QUY_DINH", "12 ký tự") in relations
    # 2 giá trị khác nhau cho CÙNG 1 khái niệm phải lộ ra CẢ 2 — để LLM tự reasoning xung đột.
    assert len({f["source_entity"] for f in facts if f["relation"] == "AP_DUNG_CHO"}) == 2


def test_concept_matches_no_concept_hit_returns_empty(monkeypatch):
    _configure_neo4j(monkeypatch)
    monkeypatch.setattr(graph_service, "_driver", lambda: _FakeDriver([[]]))
    assert graph_service.concept_matches("câu hỏi không liên quan gì") == []


def test_match_concept_names_substring_before_embedding(monkeypatch):
    concepts = [{"name": "Mật khẩu", "desc": ""}, {"name": "Thời hạn lưu trữ", "desc": ""}]

    def _boom(*a, **kw):
        raise AssertionError("không nên rơi xuống embedding fallback khi substring đã match")

    monkeypatch.setattr(graph_service.embedding_service, "embed_query", _boom)
    out = graph_service._match_concept_names("mật khẩu đăng nhập bao nhiêu ký tự", concepts, top_k=5)
    assert out == ["Mật khẩu"]


def test_match_concept_names_embedding_fallback_respects_threshold(monkeypatch):
    concepts = [{"name": "Zzz không liên quan", "desc": "abc"}]
    monkeypatch.setattr(settings, "retrieval_graph_concept_embedding_threshold", 0.65)
    monkeypatch.setattr(graph_service.embedding_service, "embed_query", lambda text: [1.0, 0.0])
    monkeypatch.setattr(graph_service.embedding_service, "embed_texts", lambda texts: [[0.0, 1.0]])  # cos=0

    out = graph_service._match_concept_names("câu hỏi lạ hoắc", concepts, top_k=5)
    assert out == []


def test_delete_by_document_calls_both_queries(monkeypatch):
    _configure_neo4j(monkeypatch)
    calls = []

    class _RecordingSession:
        def run(self, query, **params):
            calls.append((query, params))
            return _FakeResult([])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _RecordingDriver:
        def session(self):
            return _RecordingSession()

    monkeypatch.setattr(graph_service, "_driver", lambda: _RecordingDriver())
    graph_service.delete_by_document("doc-123", "TT09_2024.pdf")

    assert len(calls) == 2
    assert calls[0][1] == {"did": "doc-123"}
    assert calls[1][1] == {"title": "TT09_2024.pdf"}


def test_stats_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "neo4j_password", "")
    assert graph_service.stats() == {"configured": False}


def test_stats_shapes_counts(monkeypatch):
    _configure_neo4j(monkeypatch)
    node_rows = [{"type": "VanBan", "n": 10}, {"type": "KhaiNiem", "n": 5}]
    edge_rows = [{"type": "THAY_THE", "n": 3}]
    monkeypatch.setattr(graph_service, "_driver", lambda: _FakeDriver([node_rows, edge_rows]))

    out = graph_service.stats()
    assert out == {
        "configured": True,
        "nodes_by_type": {"VanBan": 10, "KhaiNiem": 5},
        "edges_by_type": {"THAY_THE": 3},
    }
