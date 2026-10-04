import asyncio
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.config import settings
from app.models.job import Job, JobStatus
from app.services.image_service import image_service
from app.services.job_service import job_service
from app.utils.image_processing import safe_path_join

router = APIRouter(tags=["Generation"])

@router.post("/generate")
async def generate_model(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="2D sketch drawing PNG/JPEG"),
    description: Optional[str] = Form(None, description="Optional natural language description")
):
    """
    Submits a sketch to the asynchronous reconstruction pipeline.
    Returns immediately with a tracked job_id.
    """
    # 1. Initialize tracked job
    job = job_service.create_job(description=description)
    job_dir = settings.GENERATED_DIR / job.job_id

    try:
        # 2. Persist raw user sketch safely
        raw_path = await image_service.save_uploaded_sketch(image, job_dir)
        job.input_image_path = str(raw_path)

        # 3. Dispatch pipeline execution in background
        background_tasks.add_task(
            job_service.execute_pipeline,
            job_id=job.job_id,
            input_image_path=raw_path,
            description=description
        )

        return {
            "job_id": job.job_id,
            "status": job.status
        }

    except Exception as e:
        job_service.update_job_status(job.job_id, JobStatus.FAILED, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/job/{job_id}", response_model=Job)
def get_job_status(job_id: str):
    """
    Polls the real-time status and telemetry of an ongoing or completed job.
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@router.get("/model/{job_id}")
def get_model_file(job_id: str):
    """
    Streams the reconstructed GLB binary model file to the Three.js viewer or user download.
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Model generation is not complete (current status: {job.status}).")

    try:
        job_dir = settings.GENERATED_DIR / job_id
        glb_file = safe_path_join(job_dir, "model.glb")
        
        if not glb_file.exists():
            raise HTTPException(status_code=404, detail="GLB model file not found on disk.")

        return FileResponse(
            path=str(glb_file),
            media_type="model/gltf-binary",
            filename=f"sketchforge_{job_id[:8]}.glb",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")
