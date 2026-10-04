import os
from pathlib import Path
from typing import List

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    BASE_DIR: Path = BASE_DIR
    # Environment & Hugging Face
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    MODEL_CACHE_DIR: str = os.getenv("MODEL_CACHE_DIR", str(BASE_DIR / "models"))
    
    # Device configuration
    DEVICE: str = os.getenv("DEVICE", "cuda")
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")
    MOCK_PHOTO_GENERATION: bool = os.getenv("MOCK_PHOTO_GENERATION", "false").lower() in ("true", "1", "yes")
    MAX_PHOTO_SIZE_MB: int = int(os.getenv("MAX_PHOTO_SIZE_MB", "10"))
    
    # Model configuration
    GEMMA_MODEL_ID: str = os.getenv("GEMMA_MODEL_ID", "google/gemma-4-E4B-it")
    LOAD_IN_4BIT: bool = os.getenv("LOAD_IN_4BIT", "true").lower() in ("true", "1", "yes")
    
    TRIPOSR_MODEL_ID: str = os.getenv("TRIPOSR_MODEL_ID", "stabilityai/TripoSR")
    TRIPOSR_CHUNK_SIZE: int = int(os.getenv("TRIPOSR_CHUNK_SIZE", "8192"))
    TRIPOSR_MC_RESOLUTION: int = int(os.getenv("TRIPOSR_MC_RESOLUTION", "256"))
    
    # Storage
    GENERATED_DIR: Path = BASE_DIR / "generated"
    ASSET_CACHE_DIR: Path = BASE_DIR / "assets" / "cache"

    # Asset Search & Import Pipeline Settings
    ASSET_SEARCH_ENABLED: bool = os.getenv("ASSET_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
    ASSET_AUTO_IMPORT: bool = os.getenv("ASSET_AUTO_IMPORT", "true").lower() in ("true", "1", "yes")
    ASSET_MATCH_THRESHOLD: float = float(os.getenv("ASSET_MATCH_THRESHOLD", "0.78"))
    MOCK_ASSET_SEARCH: bool = os.getenv("MOCK_ASSET_SEARCH", "false").lower() in ("true", "1", "yes")
    MAX_ASSET_SIZE_MB: int = int(os.getenv("MAX_ASSET_SIZE_MB", "100"))
    ASSET_DOWNLOAD_TIMEOUT_SEC: int = int(os.getenv("ASSET_DOWNLOAD_TIMEOUT_SEC", "30"))

    # Provider API Credentials
    SKETCHFAB_API_KEY: str = os.getenv("SKETCHFAB_API_KEY", "")
    NILO_API_KEY: str = os.getenv("NILO_API_KEY", "")
    
    # Networking & CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    @property
    def cors_origins(self) -> List[str]:
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        fe = self.FRONTEND_URL.strip()
        if fe and fe not in origins:
            origins.append(fe)
        # Additional allowed origins via comma-separated ENV if needed
        extra = os.getenv("ADDITIONAL_CORS_ORIGINS", "")
        if extra:
            for item in extra.split(","):
                item_clean = item.strip()
                if item_clean and item_clean not in origins:
                    origins.append(item_clean)
        return origins

settings = Settings()

# Ensure directories exist
settings.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
settings.ASSET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
Path(settings.MODEL_CACHE_DIR).mkdir(parents=True, exist_ok=True)
