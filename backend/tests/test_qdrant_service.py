"""Test offline cho adapter Qdrant, không cần Qdrant server."""

from qdrant_client.http import models as qm

from app.services import qdrant_service


def test_set_active_uses_points_argument(monkeypatch):
    calls: list[dict] = []

    class FakeClient:
        def collection_exists(self, collection_name: str) -> bool:
            return True

        # Signature strict để test bắt được lỗi truyền nhầm ``points_selector``.
        def set_payload(self, collection_name: str, payload: dict, points) -> None:
            calls.append(
                {
                    "collection_name": collection_name,
                    "payload": payload,
                    "points": points,
                }
            )

    monkeypatch.setattr(qdrant_service, "_client", lambda: FakeClient())

    qdrant_service.set_active("doc-123", False)

    assert len(calls) == 1
    call = calls[0]
    assert call["collection_name"] == qdrant_service.settings.qdrant_collection
    assert call["payload"] == {"is_active": False}
    assert isinstance(call["points"], qm.FilterSelector)
    condition = call["points"].filter.must[0]
    assert condition.key == "document_id"
    assert condition.match.value == "doc-123"
