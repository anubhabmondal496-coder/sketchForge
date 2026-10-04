import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.models.asset import AssetSearchResult, AssetMetadata
from app.services.providers.base_provider import BaseAssetProvider

logger = logging.getLogger("sketchforge.providers.sketchfab")

class SketchfabProvider(BaseAssetProvider):
    """
    Integrates with the official Sketchfab Data API v3.
    Searches downloadable Creative Commons 3D models.
    Respects legal constraints: only downloads when downloadable=True and authorized.
    """

    API_BASE = "https://api.sketchfab.com/v3"

    @property
    def provider_id(self) -> str:
        return "sketchfab"

    @property
    def display_name(self) -> str:
        return "Sketchfab"

    def is_available(self) -> bool:
        # Provider search can work publicly; downloading requires API token
        return True

    def _get_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if settings.SKETCHFAB_API_KEY:
            headers["Authorization"] = f"Token {settings.SKETCHFAB_API_KEY}"
        return headers

    async def search(
        self,
        query: str,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[AssetSearchResult]:
        search_q = query
        if not search_q and search_terms:
            search_q = " ".join(search_terms[:3])

        if not search_q:
            return []

        endpoint = f"{self.API_BASE}/search"
        params = {
            "type": "models",
            "q": search_q,
            "downloadable": "true",
            "archives_flavors": "false",
            "sort_by": "-likeCount",
            "count": str(min(limit, 24)),
        }

        results: List[AssetSearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params, headers=self._get_headers())
                if resp.status_code != 200:
                    logger.warning(f"Sketchfab API search responded with HTTP {resp.status_code}")
                    return []

                data = resp.json()
                for item in data.get("results", []):
                    uid = item.get("uid")
                    name = item.get("name", "Untitled")
                    user = item.get("user", {}).get("displayName") or item.get("user", {}).get("username", "Unknown")
                    license_info = item.get("license", {}).get("label", "CC BY")
                    viewer_url = item.get("viewerUrl", f"https://sketchfab.com/3d-models/{uid}")

                    # Thumbnails
                    thumbnails = item.get("thumbnails", {}).get("images", [])
                    thumb_url = thumbnails[-1].get("url") if thumbnails else None

                    is_dl = item.get("isDownloadable", False)
                    attribution = f"'{name}' by {user} under {license_info} on Sketchfab ({viewer_url})"

                    meta = AssetMetadata(
                        source="Sketchfab",
                        provider=self.provider_id,
                        asset_id=uid,
                        author=user,
                        license=license_info,
                        source_url=viewer_url,
                        attribution=attribution
                    )

                    result = AssetSearchResult(
                        provider=self.provider_id,
                        id=uid,
                        name=name,
                        thumbnail_url=thumb_url,
                        preview_url=viewer_url,
                        download_url=None, # Resolved via get_download_url if token present
                        format="glb",
                        license=license_info,
                        author=user,
                        attribution=attribution,
                        score=0.85,
                        downloadable=is_dl,
                        metadata=meta
                    )
                    results.append(result)

        except Exception as e:
            logger.warning(f"Sketchfab search failed: {e}. Gracefully continuing.")
            return []

        return results

    async def get_download_url(self, asset_id: str) -> Optional[str]:
        """
        Fetches the direct GLB download link via Sketchfab API download endpoint.
        Requires official SKETCHFAB_API_KEY.
        """
        if not settings.SKETCHFAB_API_KEY:
            logger.info("Sketchfab download requested but SKETCHFAB_API_KEY is not configured.")
            return None

        endpoint = f"{self.API_BASE}/models/{asset_id}/download"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    # Look for glb or gltf download archive
                    glb_info = data.get("glb") or data.get("gltf")
                    if glb_info and "url" in glb_info:
                        return glb_info["url"]
                else:
                    logger.warning(f"Sketchfab download url failed: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Sketchfab download url exception: {e}")

        return None
