from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.scene_spec import SceneSpec
from app.models.asset import AssetMetadata, AssetSearchResult

class JobStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    ANALYZING = "analyzing"
    SEARCHING = "searching"
    FOUND = "found"
    DOWNLOADING = "downloading"
    IMPORTING = "importing"
    GENERATING = "generating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    READY = "ready"
    FAILED = "failed"

class Job(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    stage_message: Optional[str] = "Job queued for processing"
    scene_spec: Optional[SceneSpec] = None
    model_url: Optional[str] = None
    generation_time: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    input_image_path: Optional[str] = None
    processed_image_path: Optional[str] = None
    model_path: Optional[str] = None
    description: Optional[str] = None
    refinement_prompt: Optional[str] = None
    
    # Asset pipeline extensions
    source_type: Optional[str] = "ai_generation" # "asset_search" or "ai_generation"
    asset_metadata: Optional[AssetMetadata] = None
    search_results: Optional[List[AssetSearchResult]] = None

