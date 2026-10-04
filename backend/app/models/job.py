from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.models.scene_spec import SceneSpec

class JobStatus(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    PROCESSING = "processing"
    COMPLETED = "completed"
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
