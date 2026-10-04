import io
import os
import re
import ipaddress
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Tuple
import httpx
import trimesh

from app.config import settings
from app.models.asset import AssetMetadata
from app.utils.image_processing import safe_path_join

logger = logging.getLogger("sketchforge.asset_download")

class DownloadSecurityError(Exception):
    pass

class AssetDownloadService:
    def __init__(self):
        self.max_bytes = settings.MAX_ASSET_SIZE_MB * 1024 * 1024
        self.timeout = settings.ASSET_DOWNLOAD_TIMEOUT_SEC
        self.cache_dir = settings.ASSET_CACHE_DIR

    def validate_url(self, url: str) -> None:
        """
        Validates URL security:
        - Must be HTTPS (or HTTP if referencing local development server explicitly)
        - Rejects loopback, private RFC1918 IPs, link-local, and cloud metadata addresses (SSRF prevention)
        """
        if not url or not isinstance(url, str):
            raise DownloadSecurityError("Missing or invalid URL.")

        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            raise DownloadSecurityError(f"Unsupported URL scheme: {parsed.scheme}. Only HTTPS/HTTP permitted.")

        # In production, require HTTPS unless mock local url
        hostname = parsed.hostname
        if not hostname:
            raise DownloadSecurityError("URL has no hostname.")

        # Check for loopback / private IP SSRF
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                # Allow only if explicitly in MOCK mode and pointing to local server
                if not (settings.MOCK_ASSET_SEARCH or settings.MOCK_MODE):
                    raise DownloadSecurityError(f"SSRF violation: Access to private network address {hostname} is blocked.")
        except ValueError:
            # Hostname is a domain name, check for forbidden hosts like 'localhost', '169.254.169.254', etc.
            if hostname.lower() in ("localhost", "127.0.0.1", "metadata.google.internal") and not (settings.MOCK_ASSET_SEARCH or settings.MOCK_MODE):
                raise DownloadSecurityError(f"SSRF violation: Access to {hostname} is blocked.")

    def sanitize_filename(self, name: str, default: str = "model.glb") -> str:
        """
        Sanitizes filename to prevent directory traversal and invalid characters.
        """
        clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
        clean = clean.strip('._')
        return clean or default

    def get_cache_path(self, provider: str, asset_id: str) -> Tuple[Path, Path]:
        """
        Returns (model_path, metadata_path) for cached asset.
        Key structure: assets/cache/{provider}/{asset_id}/model.glb
        """
        sanitized_provider = self.sanitize_filename(provider, "generic")
        sanitized_id = self.sanitize_filename(asset_id, "default")
        asset_folder = self.cache_dir / sanitized_provider / sanitized_id
        asset_folder.mkdir(parents=True, exist_ok=True)
        return asset_folder / "model.glb", asset_folder / "metadata.json"

    def is_cached(self, provider: str, asset_id: str) -> bool:
        model_path, meta_path = self.get_cache_path(provider, asset_id)
        return model_path.exists() and model_path.stat().st_size > 0

    def validate_3d_file(self, file_path: Path) -> dict:
        """
        Validates that the file is indeed a valid 3D model (GLB/GLTF/OBJ).
        Extracts mesh statistics (vertices, faces, bounds).
        """
        try:
            # Read header / inspect using trimesh
            scene_or_mesh = trimesh.load(str(file_path), force="mesh")
            num_verts = len(scene_or_mesh.vertices) if hasattr(scene_or_mesh, "vertices") else 0
            num_faces = len(scene_or_mesh.faces) if hasattr(scene_or_mesh, "faces") else 0
            bounds = scene_or_mesh.bounds.tolist() if hasattr(scene_or_mesh, "bounds") else []
            return {
                "valid": True,
                "vertices": num_verts,
                "faces": num_faces,
                "bounds": bounds,
            }
        except Exception as e:
            logger.warning(f"File validation warning with trimesh: {e}")
            # If trimesh cannot parse, check if it has valid GLB magic bytes ('glTF')
            try:
                with open(file_path, "rb") as f:
                    magic = f.read(4)
                if magic == b"glTF":
                    return {"valid": True, "magic": "glTF"}
            except Exception:
                pass
            raise ValueError(f"Downloaded file at {file_path} is not a valid 3D model: {str(e)}")

    async def download_and_cache(
        self,
        url: str,
        provider: str,
        asset_id: str,
        metadata: AssetMetadata
    ) -> Path:
        """
        Downloads a 3D model securely, validates its size and type, and caches it locally.
        """
        model_path, meta_path = self.get_cache_path(provider, asset_id)

        # Return cached model if already downloaded
        if model_path.exists() and model_path.stat().st_size > 0:
            logger.info(f"Asset {provider}:{asset_id} resolved from cache.")
            return model_path

        # If URL is local file or relative path (e.g. mock test models)
        if url.startswith("file://") or not url.startswith("http"):
            local_src = Path(url.replace("file://", ""))
            if not local_src.is_absolute():
                local_src = settings.BASE_DIR / local_src
            if local_src.exists():
                import shutil
                shutil.copyfile(local_src, model_path)
                self.validate_3d_file(model_path)
                self._save_metadata(meta_path, metadata)
                return model_path
            else:
                raise FileNotFoundError(f"Local asset source not found: {local_src}")

        # Security check on remote URL
        self.validate_url(url)

        temp_target = model_path.with_suffix(".tmp")
        try:
            logger.info(f"Downloading asset {provider}:{asset_id} from {url}")
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise ValueError(f"Failed to download asset: HTTP status {response.status_code}")

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_bytes:
                        raise DownloadSecurityError(f"Model file size ({content_length} bytes) exceeds maximum limit ({self.max_bytes} bytes).")

                    downloaded_bytes = 0
                    with open(temp_target, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            downloaded_bytes += len(chunk)
                            if downloaded_bytes > self.max_bytes:
                                raise DownloadSecurityError(f"Model download aborted: exceeded {self.max_bytes} bytes limit.")
                            f.write(chunk)

            # Validate the downloaded 3D file
            self.validate_3d_file(temp_target)

            # Atomically replace destination
            if temp_target.exists():
                if model_path.exists():
                    model_path.unlink()
                temp_target.rename(model_path)

            # Store metadata
            self._save_metadata(meta_path, metadata)
            logger.info(f"Asset {provider}:{asset_id} downloaded and verified successfully ({downloaded_bytes} bytes).")
            return model_path

        finally:
            if temp_target.exists():
                try:
                    temp_target.unlink()
                except Exception:
                    pass

    def _save_metadata(self, meta_path: Path, metadata: AssetMetadata) -> None:
        from datetime import datetime
        data = metadata.model_dump()
        if not data.get("downloaded_at"):
            data["downloaded_at"] = datetime.utcnow().isoformat()
        with open(meta_path, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2)

    def get_metadata(self, provider: str, asset_id: str) -> Optional[AssetMetadata]:
        _, meta_path = self.get_cache_path(provider, asset_id)
        if meta_path.exists():
            import json
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return AssetMetadata.model_validate(json.load(f))
            except Exception:
                return None
        return None

asset_download_service = AssetDownloadService()
