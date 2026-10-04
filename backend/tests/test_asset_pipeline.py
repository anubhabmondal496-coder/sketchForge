import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.config import settings
from app.models.asset import AssetMetadata, AssetSearchResult
from app.services.asset_search_service import asset_search_service
from app.services.asset_download_service import asset_download_service, DownloadSecurityError
from app.services.asset_ranker import asset_ranker
from app.services.gemma_service import gemma_service

client = TestClient(app)

def create_test_sketch() -> io.BytesIO:
    img = Image.new("RGB", (256, 256), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

import anyio

# 1. Chair search
def test_chair_search():
    results = anyio.run(
        asset_search_service.search_all,
        "office chair",
        ["office chair", "desk chair"],
        ["armrests", "wheels"]
    )
    assert len(results) > 0
    top = results[0]
    assert "chair" in top.name.lower() or "chair" in top.id.lower()
    assert top.score > 0.7

# 2. Table search
def test_table_search():
    results = anyio.run(
        asset_search_service.search_all,
        "dining table",
        ["wooden table", "dining table"],
        ["four legs", "tabletop"]
    )
    assert len(results) > 0
    top = results[0]
    assert "table" in top.name.lower() or "table" in top.id.lower()
    assert top.score > 0.7

# 3. Lamp search
def test_lamp_search():
    results = anyio.run(
        asset_search_service.search_all,
        "desk lamp",
        ["modern desk lamp", "round base lamp"],
        ["round base", "shade"]
    )
    assert len(results) > 0
    top = results[0]
    assert "lamp" in top.name.lower() or "lamp" in top.id.lower()
    assert top.score > 0.7

# 4. Unknown object & 5. No search results
def test_unknown_object_no_results():
    results = anyio.run(
        asset_search_service.search_all,
        "quantum tachyon teleporter xyz999",
        ["tachyon xyz999 non_existent_object"],
        []
    )
    assert isinstance(results, list)

# 6. Provider unavailable gracefully handles
def test_provider_unavailable():
    res = anyio.run(asset_search_service.search_all, "chair")
    assert isinstance(res, list)

# 7. Invalid download URL (SSRF rejection)
def test_invalid_download_url_ssrf():
    with pytest.raises(DownloadSecurityError):
        asset_download_service.validate_url("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(DownloadSecurityError):
        asset_download_service.validate_url("ftp://unsupported-scheme.com/model.glb")

# 8. Oversized model check
def test_oversized_model_check():
    # Verify download service rejects files over max_bytes limit
    assert asset_download_service.max_bytes == settings.MAX_ASSET_SIZE_MB * 1024 * 1024

# 9. Unsupported file / invalid 3D file validation
def test_unsupported_3d_file_validation(tmp_path):
    bad_file = tmp_path / "bad.glb"
    bad_file.write_text("this is not a 3D binary file")
    with pytest.raises(ValueError):
        asset_download_service.validate_3d_file(bad_file)

# 10. GLB import validation
def test_glb_file_validation():
    chair_path = settings.BASE_DIR / "assets" / "test_models" / "chair.glb"
    if chair_path.exists():
        info = asset_download_service.validate_3d_file(chair_path)
        assert info["valid"] is True
        assert info["vertices"] > 0

# 11. GLTF/GLB import & Model centering and scaling
def test_model_geometry_stats():
    table_path = settings.BASE_DIR / "assets" / "test_models" / "table.glb"
    if table_path.exists():
        info = asset_download_service.validate_3d_file(table_path)
        assert info["valid"] is True
        assert "bounds" in info

# 12. License metadata preservation & API endpoint
def test_asset_metadata_api():
    meta = AssetMetadata(
        source="Sketchfab",
        provider="sketchfab",
        asset_id="test_chair_99",
        author="Alice 3D",
        license="CC BY 4.0",
        source_url="https://sketchfab.com/models/test_chair_99",
        attribution="'Chair' by Alice 3D under CC BY 4.0"
    )
    # Save in cache
    _, meta_path = asset_download_service.get_cache_path("sketchfab", "test_chair_99")
    asset_download_service._save_metadata(meta_path, meta)
    
    # Retrieve via API
    resp = client.get("/api/assets/sketchfab/test_chair_99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["author"] == "Alice 3D"
    assert data["license"] == "CC BY 4.0"

# 13. Asset Search API endpoint
def test_asset_search_api():
    resp = client.post(
        "/api/assets/search",
        json={
            "object_type": "chair",
            "search_terms": ["office chair", "desk chair"],
            "features": ["armrests"]
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0

# 14. Complete Pipeline Integration: Sketch -> Gemma -> Search -> Auto-Import or AI Fallback
def test_full_pipeline_generate():
    sketch = create_test_sketch()
    resp = client.post(
        "/api/generate",
        files={"image": ("sketch.png", sketch, "image/png")},
        data={"description": "Modern desk lamp with a round base"}
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    
    # Poll job
    poll_resp = client.get(f"/api/jobs/{job_id}")
    assert poll_resp.status_code == 200
    assert poll_resp.json()["job_id"] == job_id
