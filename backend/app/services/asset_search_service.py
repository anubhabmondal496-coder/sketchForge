import asyncio
import logging
from typing import List, Optional

from app.config import settings
from app.models.asset import AssetSearchResult, AssetMetadata
from app.services.providers.base_provider import BaseAssetProvider
from app.services.providers.sketchfab_provider import SketchfabProvider
from app.services.providers.nilo_provider import NiloProvider
from app.services.providers.mock_provider import MockAssetProvider
from app.services.asset_ranker import asset_ranker

logger = logging.getLogger("sketchforge.asset_search")

class AssetSearchService:
    def __init__(self):
        # Register available providers in priority order
        self.providers: List[BaseAssetProvider] = [
            SketchfabProvider(),
            NiloProvider(),
            MockAssetProvider(),
        ]

    def get_provider(self, provider_id: str) -> Optional[BaseAssetProvider]:
        for p in self.providers:
            if p.provider_id.lower() == provider_id.lower():
                return p
        return None

    async def search_all(
        self,
        object_type: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None,
        limit_per_provider: int = 6
    ) -> List[AssetSearchResult]:
        """
        Executes concurrent searches across all operational providers.
        Aggregates results and ranks them using multi-factor scoring.
        """
        if not settings.ASSET_SEARCH_ENABLED:
            logger.info("Asset search is disabled via settings.")
            return []

        primary_query = object_type or (search_terms[0] if search_terms else "")

        tasks = []
        for provider in self.providers:
            # If in mock asset search mode, skip external providers or prioritize mock
            if settings.MOCK_ASSET_SEARCH and provider.provider_id != "mock":
                continue

            if provider.is_available():
                tasks.append(
                    provider.search(
                        query=primary_query,
                        search_terms=search_terms,
                        features=features,
                        style=style,
                        limit=limit_per_provider
                    )
                )

        if not tasks:
            return []

        # Run provider searches concurrently with error suppression
        gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: List[AssetSearchResult] = []
        for res in gathered_results:
            if isinstance(res, list):
                combined.extend(res)
            elif isinstance(res, Exception):
                logger.warning(f"Provider search exception: {res}")

        # Rank all combined results
        ranked = asset_ranker.rank_results(
            combined,
            object_type=object_type,
            search_terms=search_terms,
            features=features,
            style=style
        )

        return ranked

asset_search_service = AssetSearchService()
