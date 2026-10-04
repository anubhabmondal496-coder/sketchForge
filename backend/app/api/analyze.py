import uuid
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import settings
from app.models.scene_spec import SceneSpec
from app.services.image_service import image_service
from app.services.gemma_service import gemma_service

router = APIRouter(tags=["Analyze"])

@router.post("/analyze")
@router.post("/api/analyze")
async def analyze_sketch(
    image: UploadFile = File(..., description="2D sketch drawing PNG/JPEG"),
    description: Optional[str] = Form(None, description="Optional natural language description")
):
    """
    Submits a sketch and optional prompt directly to Gemma 4 E4B
    for multimodal reasoning. Returns structured visual reasoning JSON
    with normalized search terms, features, and SceneSpec.
    """
    temp_id = f"temp_{uuid.uuid4()}"
    temp_dir = settings.GENERATED_DIR / temp_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        raw_path = await image_service.save_uploaded_sketch(image, temp_dir)
        processed_path = image_service.prepare_for_inference(raw_path, temp_dir)

        # 1. Visual reasoning & search query generation (Step 1)
        analysis = gemma_service.analyze_sketch_understanding(
            image_path=processed_path,
            description=description
        )

        # 2. Geometry specification (SceneSpec)
        spec = gemma_service.analyze(
            image_path=processed_path,
            description=description
        )

        # Return combined structure compatible with both SceneSpec expectations and GemmaAnalysisResult
        res_data = spec.model_dump()
        res_data.update({
            "object_type": analysis.object_type,
            "canonical_name": analysis.canonical_name,
            "search_terms": analysis.search_terms,
            "features": analysis.features,
            "approximate_scale": analysis.approximate_scale,
        })
        return res_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal analysis failed: {str(e)}")

    finally:
        # Clean up temporary upload directory
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
