from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class GemmaAnalysisResult(BaseModel):
    object_type: str = Field(description="Identified object type (e.g. office chair, table, desk lamp)")
    canonical_name: str = Field(description="Canonical normalized name")
    search_terms: List[str] = Field(default_factory=list, description="Extracted keywords and queries for asset search")
    style: List[str] = Field(default_factory=list, description="Style keywords (e.g. modern, wooden, minimalist)")
    features: List[str] = Field(default_factory=list, description="Key physical features (e.g. armrests, round base)")
    components: List[str] = Field(default_factory=list, description="Major physical components")
    materials: List[str] = Field(default_factory=list, description="Materials (e.g. fabric, plastic, metal)")
    colors: List[str] = Field(default_factory=list, description="Colors detected or requested")
    user_modifications: List[str] = Field(default_factory=list, description="User requested modifications")
    detected_objects: List[str] = Field(default_factory=list, description="All recognizable objects detected in photo")
    needs_clarification: bool = Field(default=False, description="Whether user needs to clarify between multiple objects")
    clarification_question: Optional[str] = Field(default=None, description="Clarification prompt for user")
    approximate_scale: Optional[str] = Field(default="human-sized", description="Approximate scale or dimensions")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Visual reasoning confidence")

class AssetMetadata(BaseModel):
    source: str = Field(description="Source repository or provider name")
    provider: str = Field(description="Provider identifier (e.g. sketchfab, nilo, mock)")
    asset_id: str = Field(description="Unique asset identifier in the provider system")
    author: Optional[str] = Field(default="Unknown", description="Model creator or author")
    license: Optional[str] = Field(default="CC BY", description="Model usage license")
    source_url: Optional[str] = Field(default="", description="Web page or view URL for attribution")
    attribution: Optional[str] = Field(default="", description="Attribution text required by license")
    downloaded_at: Optional[str] = Field(default=None, description="ISO timestamp when asset was imported/cached")

class AssetSearchResult(BaseModel):
    provider: str
    id: str
    name: str
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    format: str = "glb"
    license: Optional[str] = "CC BY"
    author: Optional[str] = "Unknown"
    attribution: Optional[str] = ""
    score: float = 0.0
    downloadable: bool = True
    metadata: Optional[AssetMetadata] = None

class AssetSearchRequest(BaseModel):
    object_type: Optional[str] = None
    search_terms: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    style: List[str] = Field(default_factory=list)

class AssetSearchResponse(BaseModel):
    results: List[AssetSearchResult] = Field(default_factory=list)
    total: int = 0
    best_match: Optional[AssetSearchResult] = None

class AssetImportRequest(BaseModel):
    provider: str
    asset_id: str
    download_url: Optional[str] = None
    name: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    source_url: Optional[str] = None
    attribution: Optional[str] = None

class AssetImportResponse(BaseModel):
    success: bool
    asset_id: str
    provider: str
    model_url: str
    cached: bool = False
    metadata: AssetMetadata
