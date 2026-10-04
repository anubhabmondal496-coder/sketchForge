from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.asset import AssetSearchResult, AssetMetadata

class BaseAssetProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'sketchfab', 'nilo', 'mock')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """User-friendly name of the provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is currently configured and operational."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[AssetSearchResult]:
        """Searches the provider for 3D assets conforming to the request."""
        pass

    @abstractmethod
    async def get_download_url(self, asset_id: str) -> Optional[str]:
        """Resolves the direct download URL for a downloadable asset if authorized."""
        pass
