import logging
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.models.asset import AssetSearchResult, AssetMetadata
from app.services.providers.base_provider import BaseAssetProvider

logger = logging.getLogger("sketchforge.providers.mock")

class MockAssetProvider(BaseAssetProvider):
    """
    Mock & Offline Asset Provider.
    Supplies high quality pre-packaged CC0 3D models for hackathon demos,
    offline testing, and local development (Chair, Table, Lamp, etc.).
    """

    MOCK_CATALOG = [
        {
            "id": "mock_chair_01",
            "name": "Modern Ergonomic Office Chair",
            "keywords": ["chair", "office chair", "desk chair", "computer chair", "armrests", "seat"],
            "features": ["armrests", "wheels", "backrest", "ergonomic"],
            "style": ["modern", "office", "minimalist"],
            "filename": "chair.glb",
            "author": "SketchForge Open Library",
            "license": "CC0 Public Domain",
            "attribution": "Public Domain 3D Chair Asset (SketchForge Test Assets)",
            "thumbnail_url": "/test-models/chair_thumb.png",
        },
        {
            "id": "mock_table_01",
            "name": "Minimalist Wooden Dining Table",
            "keywords": ["table", "desk", "dining table", "wooden table", "legs", "surface"],
            "features": ["four legs", "wooden surface", "sturdy"],
            "style": ["wooden", "modern", "minimalist"],
            "filename": "table.glb",
            "author": "SketchForge Open Library",
            "license": "CC0 Public Domain",
            "attribution": "Public Domain 3D Table Asset (SketchForge Test Assets)",
            "thumbnail_url": "/test-models/table_thumb.png",
        },
        {
            "id": "mock_lamp_01",
            "name": "Modern Desk Lamp with Round Base",
            "keywords": ["lamp", "desk lamp", "light", "table lamp", "lantern", "shade"],
            "features": ["round base", "conical shade", "slender stem"],
            "style": ["modern", "metallic", "minimalist"],
            "filename": "lamp.glb",
            "author": "SketchForge Open Library",
            "license": "CC0 Public Domain",
            "attribution": "Public Domain 3D Lamp Asset (SketchForge Test Assets)",
            "thumbnail_url": "/test-models/lamp_thumb.png",
        },
        {
            "id": "mock_house_01",
            "name": "Suburban Cottage House with Pitched Roof",
            "keywords": ["house", "home", "building", "cottage", "cabin", "residence", "villa", "roof"],
            "features": ["pitched roof", "chimney", "front door", "windows"],
            "style": ["suburban", "architectural", "cottage"],
            "filename": "house.glb",
            "author": "SketchForge Open Architecture",
            "license": "CC0 Public Domain",
            "attribution": "Public Domain 3D House Asset (SketchForge Architecture)",
            "thumbnail_url": "/test-models/house_thumb.png",
        },
    ]

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def display_name(self) -> str:
        return "SketchForge Open Library"

    def is_available(self) -> bool:
        return True

    def _get_local_file_path(self, filename: str) -> Optional[Path]:
        # Check backend assets test_models
        p1 = settings.BASE_DIR / "assets" / "test_models" / filename
        if p1.exists():
            return p1
        # Check frontend public test-models
        p2 = settings.BASE_DIR.parent / "frontend" / "public" / "test-models" / filename
        if p2.exists():
            return p2
        return None

    async def search(
        self,
        query: str,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[AssetSearchResult]:
        q_lower = (query or "").lower()
        terms_lower = [t.lower() for t in (search_terms or [])]
        features_lower = [f.lower() for f in (features or [])]

        all_needles = set()
        if q_lower:
            all_needles.update(q_lower.split())
        for t in terms_lower:
            all_needles.update(t.split())
        for f in features_lower:
            all_needles.update(f.split())

        results: List[AssetSearchResult] = []

        for item in self.MOCK_CATALOG:
            item_keywords = set(item["keywords"] + item["features"] + item["style"])
            item_name_words = set(item["name"].lower().split())

            # Check overlap
            overlap = all_needles.intersection(item_keywords | item_name_words)
            if overlap:
                file_path = self._get_local_file_path(item["filename"])
                file_url = f"file://{file_path}" if file_path else f"/test-models/{item['filename']}"

                meta = AssetMetadata(
                    source="SketchForge Open Library",
                    provider=self.provider_id,
                    asset_id=item["id"],
                    author=item["author"],
                    license=item["license"],
                    source_url="https://sketchforge.dev/assets",
                    attribution=item["attribution"]
                )

                res = AssetSearchResult(
                    provider=self.provider_id,
                    id=item["id"],
                    name=item["name"],
                    thumbnail_url=item["thumbnail_url"],
                    preview_url=file_url,
                    download_url=file_url,
                    format="glb",
                    license=item["license"],
                    author=item["author"],
                    attribution=item["attribution"],
                    score=0.92,
                    downloadable=True,
                    metadata=meta
                )
                results.append(res)

        return results[:limit]

    async def get_download_url(self, asset_id: str) -> Optional[str]:
        for item in self.MOCK_CATALOG:
            if item["id"] == asset_id:
                file_path = self._get_local_file_path(item["filename"])
                if file_path:
                    return f"file://{file_path}"
        return None
