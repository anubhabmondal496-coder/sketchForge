import re
from typing import List, Dict, Any, Optional
from app.models.asset import AssetSearchResult

class AssetRanker:
    """
    Ranks 3D asset search candidates based on multi-factor scoring:
    - semantic similarity to requested query/terms (0.35)
    - object category match (0.25)
    - requested features match (0.15)
    - format quality (GLB/GLTF preferred) (0.10)
    - license compatibility (CC0, CC-BY, Public Domain) (0.10)
    - provider confidence (0.05)
    """

    DEFAULT_WEIGHTS = {
        "semantic_similarity": 0.35,
        "category_match": 0.25,
        "feature_match": 0.15,
        "format_quality": 0.10,
        "license_quality": 0.10,
        "provider_confidence": 0.05,
    }

    FORMAT_SCORES = {
        "glb": 1.0,
        "gltf": 0.9,
        "fbx": 0.6,
        "obj": 0.5,
    }

    LICENSE_SCORES = {
        "cc0": 1.0,
        "public domain": 1.0,
        "cc-by": 0.9,
        "cc by": 0.9,
        "cc-by-sa": 0.8,
        "cc by-sa": 0.8,
        "standard": 0.6,
        "editorial": 0.3,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def _normalize_tokens(self, text: str) -> set:
        if not text:
            return set()
        clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = set(clean.split())
        # Strip common stopwords
        stopwords = {"a", "an", "the", "and", "or", "with", "of", "in", "for", "to"}
        return tokens - stopwords

    def calculate_score(
        self,
        candidate: AssetSearchResult,
        object_type: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None
    ) -> float:
        name_tokens = self._normalize_tokens(candidate.name)
        desc_tokens = self._normalize_tokens(f"{candidate.name} {candidate.attribution or ''} {candidate.author or ''}")

        # 1. Category match
        category_match = 0.0
        if object_type:
            target_cat_tokens = self._normalize_tokens(object_type)
            if target_cat_tokens and (target_cat_tokens.issubset(name_tokens) or any(t in name_tokens for t in target_cat_tokens)):
                category_match = 1.0
            elif target_cat_tokens and any(t in desc_tokens for t in target_cat_tokens):
                category_match = 0.7

        # 2. Semantic / term similarity
        terms = search_terms or []
        term_matches = 0
        total_term_tokens = 0
        for term in terms:
            tt = self._normalize_tokens(term)
            total_term_tokens += len(tt)
            for t in tt:
                if t in name_tokens:
                    term_matches += 1.0
                elif t in desc_tokens:
                    term_matches += 0.5

        semantic_similarity = (term_matches / max(1, total_term_tokens)) if total_term_tokens > 0 else 0.5
        semantic_similarity = min(1.0, semantic_similarity)

        # 3. Feature match
        req_features = features or []
        feat_matches = 0
        for f in req_features:
            f_tokens = self._normalize_tokens(f)
            if any(ft in desc_tokens or ft in name_tokens for ft in f_tokens):
                feat_matches += 1
        feature_match = (feat_matches / len(req_features)) if req_features else 0.7

        # 4. Format quality
        fmt = (candidate.format or "glb").lower()
        format_quality = self.FORMAT_SCORES.get(fmt, 0.4)

        # 5. License quality
        lic = (candidate.license or "cc-by").lower()
        license_quality = 0.6
        for k, v in self.LICENSE_SCORES.items():
            if k in lic:
                license_quality = v
                break

        # 6. Provider confidence
        provider_confidence = 0.9 if candidate.downloadable else 0.2

        score = (
            semantic_similarity * self.weights.get("semantic_similarity", 0.35)
            + category_match * self.weights.get("category_match", 0.25)
            + feature_match * self.weights.get("feature_match", 0.15)
            + format_quality * self.weights.get("format_quality", 0.10)
            + license_quality * self.weights.get("license_quality", 0.10)
            + provider_confidence * self.weights.get("provider_confidence", 0.05)
        )

        return round(float(score), 3)

    def rank_results(
        self,
        results: List[AssetSearchResult],
        object_type: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
        style: Optional[List[str]] = None
    ) -> List[AssetSearchResult]:
        for res in results:
            res.score = self.calculate_score(
                res,
                object_type=object_type,
                search_terms=search_terms,
                features=features,
                style=style
            )

        # Sort descending by score, prioritizing downloadable assets
        sorted_results = sorted(results, key=lambda x: (x.downloadable, x.score), reverse=True)
        return sorted_results

asset_ranker = AssetRanker()
