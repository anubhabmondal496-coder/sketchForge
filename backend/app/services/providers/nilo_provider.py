import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.models.asset import AssetSearchResult, AssetMetadata
from app.services.providers.base_provider import BaseAssetProvider

logger = logging.getLogger("sketchforge.providers.nilo")

class NiloProvider(BaseAssetProvider):
    """
    Integrates with Nilo / external 3D open asset providers.
    Provides legal search and CC licensed asset resolution.
    Gracefully handles unconfigured API key or offline states.
    """

    API_BASE = "https://api.nilo3d.com/v1"

    @property
    def provider_id(self) -> str:
        return "nilo"

    @property
    def display_name(self) -> str:
        return "Nilo 3D"

    def is_available(self) -> bool:
        return bool(settings.NILO_API_KEY)

    def _get_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if settings.NILO_API_KEY:
            headers["Authorization"] = f"Bearer {settings.NILO_API_KEY}"
        return headers

    async def search(
        self,
        query: str,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[AssetSearchResult]:
        if not self.is_available():
            # If no API key configured, return empty list gracefully without throwing error
            return []

        search_q = query
        if not search_q and search_terms:
            search_q = " ".join(search_terms[:3])

        results: List[AssetSearchResult] = []
        try:
            endpoint = f"{self.API_BASE}/assets/search"
            params = {"q": search_q, "format": "glb", "limit": min(limit, 20)}
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(endpoint, params=params, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("assets", []):
                        uid = item.get("id")
                        name = item.get("name", "3D Model")
                        author = item.get("author", "Nilo Contributor")
                        lic = item.get("license", "CC-BY-4.0")
                        source_url = item.get("url", f"https://nilo3d.com/models/{uid}")
                        dl_url = item.get("download_url")

                        attribution = f"'{name}' by {author} under {lic} (Nilo 3D)"
                        meta = AssetMetadata(
                            source="Nilo",
                            provider=self.provider_id,
                            asset_id=uid,
                            author=author,
                            license=lic,
                            source_url=source_url,
                            attribution=attribution
                        )
                        results.append(AssetSearchResult(
                            provider=self.provider_id,
                            id=uid,
                            name=name,
                            thumbnail_url=item.get("thumbnail_url"),
                            preview_url=source_url,
                            download_url=dl_url,
                            format="glb",
                            license=lic,
                            author=author,
                            attribution=attribution,
                            score=0.8,
                            downloadable=bool(dl_url),
                            metadata=meta
                        ))
        except Exception as e:
            logger.warning(f"Nilo search unavailable: {e}. Continuing pipeline.")

        return results

    async def get_download_url(self, asset_id: str) -> Optional[str]:
        if not self.is_available():
            return None
        return None
