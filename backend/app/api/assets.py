import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.config import settings
from app.models.asset import (
    AssetSearchRequest,
    AssetSearchResponse,
    AssetImportRequest,
    AssetImportResponse,
    AssetMetadata,
)
from app.services.asset_search_service import asset_search_service
from app.services.asset_download_service import asset_download_service
from app.utils.image_processing import safe_path_join

logger = logging.getLogger("sketchforge.api.assets")

router = APIRouter(prefix="/api/assets", tags=["Assets"])

@router.post("/search", response_model=AssetSearchResponse)
async def search_assets(req: AssetSearchRequest):
    """
    Step 13: Searches multiple 3D asset providers (Sketchfab, Nilo, Mock library)
    using normalized terms, features, and style from Gemma 4 E4B.
    Returns scored, ranked results.
    """
    try:
        ranked_results = await asset_search_service.search_all(
            object_type=req.object_type,
            search_terms=req.search_terms,
            features=req.features,
            style=req.style,
            limit_per_provider=6
        )

        best_match = ranked_results[0] if ranked_results else None
        return AssetSearchResponse(
            results=ranked_results,
            total=len(ranked_results),
            best_match=best_match
        )
    except Exception as e:
        logger.exception(f"Asset search endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Asset search error: {str(e)}")

@router.post("/import", response_model=AssetImportResponse)
async def import_asset(req: AssetImportRequest):
    """
    Downloads and caches a selected asset by provider and asset_id.
    Validates license, security (SSRF, size, format), and returns local model URL.
    """
    try:
        # Check if already cached
        already_cached = asset_download_service.is_cached(req.provider, req.asset_id)
        
        # If download URL is not provided in request, attempt provider lookup
        dl_url = req.download_url
        if not dl_url:
            provider = asset_search_service.get_provider(req.provider)
            if provider:
                dl_url = await provider.get_download_url(req.asset_id)

        if not dl_url and not already_cached:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot download asset {req.asset_id}: No direct download link available or authentication required."
            )

        metadata = AssetMetadata(
            source=req.provider.capitalize(),
            provider=req.provider,
            asset_id=req.asset_id,
            author=req.author or "Unknown",
            license=req.license or "CC BY",
            source_url=req.source_url or "",
            attribution=req.attribution or f"{req.name or 'Model'} from {req.provider}"
        )

        if not already_cached:
            await asset_download_service.download_and_cache(
                url=dl_url,
                provider=req.provider,
                asset_id=req.asset_id,
                metadata=metadata
            )

        # Model stream URL
        stream_url = f"/api/assets/{req.provider}/{req.asset_id}/model.glb"

        return AssetImportResponse(
            success=True,
            asset_id=req.asset_id,
            provider=req.provider,
            model_url=stream_url,
            cached=already_cached,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Import asset failed: {e}")
        raise HTTPException(status_code=400, detail=f"Asset import failed: {str(e)}")

@router.get("/{provider}/{asset_id}/model.glb")
def get_cached_asset_model(provider: str, asset_id: str):
    """
    Streams the downloaded and validated GLB model file directly to the Three.js viewer.
    """
    model_path, _ = asset_download_service.get_cache_path(provider, asset_id)
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Requested model not found in asset cache.")

    return FileResponse(
        path=str(model_path),
        media_type="model/gltf-binary",
        filename=f"{provider}_{asset_id}.glb",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.get("/{provider}/{asset_id}")
def get_asset_metadata(provider: str, asset_id: str):
    """
    Step 13: Retrieves metadata and license attribution for a stored/cached asset.
    """
    meta = asset_download_service.get_metadata(provider, asset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Asset metadata not found.")
    return meta
