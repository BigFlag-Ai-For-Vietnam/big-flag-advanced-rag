"""Unit tests cho LightRAG adapter (không gọi network)."""
from app.services import lightrag_service
from app.services.lightrag_service import build_entity_types_guidance


def test_guidance_contains_base_and_user_defined_facet_types():
    guidance = build_entity_types_guidance(
        ["Quyền lợi bảo hiểm (chính & bổ sung)", "Điều kiện loại trừ"]
    )

    assert "- DOCUMENT:" in guidance
    assert "- PRODUCT:" in guidance
    assert "- ORGANIZATION:" in guidance
    assert "- FACET_QUYEN_LOI_BAO_HIEM_CHINH_BO_SUNG:" in guidance
    assert 'facet "Quyền lợi bảo hiểm (chính & bổ sung)"' in guidance
    assert "- FACET_DIEU_KIEN_LOAI_TRU:" in guidance


def test_guidance_keeps_duplicate_type_keys_unique():
    guidance = build_entity_types_guidance(["Phí & lệ phí", "Phí lệ phí"])

    assert "- FACET_PHI_LE_PHI:" in guidance
    assert "- FACET_PHI_LE_PHI_2:" in guidance


def test_index_document_uses_document_provenance_and_same_lifecycle(monkeypatch):
    calls = []

    class FakeRag:
        async def initialize_storages(self):
            calls.append(("initialize",))

        async def ainsert(self, content, *, ids, file_paths):
            calls.append(("insert", content, ids, file_paths))

        async def finalize_storages(self):
            calls.append(("finalize",))

    monkeypatch.setattr(lightrag_service.settings, "lightrag_enabled", True)
    monkeypatch.setattr(lightrag_service, "_build_rag", lambda _facets: FakeRag())

    indexed = lightrag_service.index_document(
        "doc-123",
        "Family",
        "family.pdf",
        "Quyền lợi trợ cấp mai táng.",
        ["Quyền lợi bảo hiểm"],
    )

    assert indexed is True
    assert calls[0] == ("initialize",)
    assert calls[1][0] == "insert"
    assert calls[1][1].startswith("# Tài liệu: Family")
    assert calls[1][2:] == ("doc-123", "family.pdf")
    assert calls[2] == ("finalize",)
