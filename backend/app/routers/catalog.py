"""Router catalog: cung cấp preset facet-entities cho UI upload."""
from __future__ import annotations

from fastapi import APIRouter

from app.catalog_presets import list_presets
from app.schemas.document import CatalogPreset

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog-presets", response_model=list[CatalogPreset])
def get_catalog_presets():
    """Danh sách preset theo category (Thẻ / Bảo hiểm / Quy trình / Khác) cho dropdown upload."""
    return list_presets()
