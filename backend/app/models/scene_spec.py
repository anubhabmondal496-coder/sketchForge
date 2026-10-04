from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class SceneGeometry(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    width: Optional[float] = Field(default=None, description="Estimated width in meters")
    depth: Optional[float] = Field(default=None, description="Estimated depth in meters")
    height: Optional[float] = Field(default=None, description="Estimated height in meters")
    back_height: Optional[float] = Field(default=None, description="Estimated backrest height if applicable")

class SceneSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    object: str = Field(description="Identified core object class (e.g. chair, lamp, mug, table)")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    style: Optional[str] = Field(default="minimalist industrial", description="Aesthetic or design style")
    material: Optional[str] = Field(default="matte finish", description="Dominant visual material")
    components: List[str] = Field(default_factory=list, description="Constituent parts detected in the sketch")
    geometry: Optional[SceneGeometry] = Field(default_factory=SceneGeometry, description="3D proportions and bounding dimensions")
    generation_prompt: Optional[str] = Field(
        default=None, 
        description="Refined synthesis prompt prepared for 3D reconstruction"
    )
