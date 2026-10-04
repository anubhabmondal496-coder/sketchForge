import json
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from app.config import settings
from app.models.job import Job, JobStatus
from app.models.scene_spec import SceneSpec
from app.services.image_service import image_service
from app.services.gemma_service import gemma_service
from app.services.job_service import job_service
from app.utils.image_processing import safe_path_join

router = APIRouter(tags=["Refinement"])

@router.post("/refine")
async def refine_model(
    background_tasks: BackgroundTasks,
    existing_spec: str = Form(..., description="Existing SceneSpec JSON string"),
    refinement: str = Form(..., description="Natural language refinement instruction"),
    image: Optional[UploadFile] = File(None, description="Optional original sketch image")
):
    """
    Refines an existing 3D reconstruction:
    1. Gemma 4 E4B updates the SceneSpec according to the user instruction.
    2. Spawns an asynchronous job to regenerate the 3D geometry with TripoSR.
    """
    # Parse existing spec
    try:
        spec_dict = json.loads(existing_spec)
        parsed_spec = SceneSpec.model_validate(spec_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid existing SceneSpec: {str(e)}")

    if not refinement.strip():
        raise HTTPException(status_code=400, detail="Refinement text cannot be empty.")

    # Create new tracked job for the refined version
    job = job_service.create_job(
        description=parsed_spec.generation_prompt or parsed_spec.object,
        refinement_prompt=refinement.strip()
    )
    job_dir = settings.GENERATED_DIR / job.job_id

    # Handle image: either new uploaded image, or placeholder if none provided
    if image is not None:
        raw_path = await image_service.save_uploaded_sketch(image, job_dir)
    else:
        # Create a clean canvas placeholder in the job directory
        from PIL import Image as PILImage
        raw_path = safe_path_join(job_dir, "input.png")
        blank = PILImage.new("RGB", (512, 512), (255, 255, 255))
        blank.save(raw_path)

    job.input_image_path = str(raw_path)

    # Dispatch pipeline with existing_spec and refinement_prompt
    background_tasks.add_task(
        job_service.execute_pipeline,
        job_id=job.job_id,
        input_image_path=raw_path,
        description=parsed_spec.generation_prompt or parsed_spec.object,
        existing_spec=parsed_spec,
        refinement_prompt=refinement.strip()
    )

    return {
        "job_id": job.job_id,
        "status": job.status
    }
