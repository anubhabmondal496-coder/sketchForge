import os
import time
import uuid
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models.job import Job, JobStatus
from app.models.scene_spec import SceneSpec
from app.services.gemma_service import gemma_service
from app.services.tripo_service import tripo_service
from app.services.image_service import image_service
from app.utils.image_processing import safe_path_join

logger = logging.getLogger("sketchforge.jobs")

class JobService:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(
        self,
        description: Optional[str] = None,
        refinement_prompt: Optional[str] = None
    ) -> Job:
        """Creates a new tracked generation job and its storage directory."""
        job_id = str(uuid.uuid4())
        job_dir = settings.GENERATED_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        job = Job(
            job_id=job_id,
            status=JobStatus.QUEUED,
            stage_message="Job queued for processing",
            description=description,
            refinement_prompt=refinement_prompt
        )
        self._jobs[job_id] = job
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] job={job_id} created status=queued")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage_message: Optional[str] = None,
        error: Optional[str] = None
    ):
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            self._jobs[job_id].updated_at = datetime.utcnow()
            if stage_message:
                self._jobs[job_id].stage_message = stage_message
            if error:
                self._jobs[job_id].error = error

    async def execute_pipeline(
        self,
        job_id: str,
        input_image_path: Path,
        description: Optional[str] = None,
        existing_spec: Optional[SceneSpec] = None,
        refinement_prompt: Optional[str] = None
    ):
        """
        Executes the full SketchForge generation pipeline asynchronously:
        1. Preprocess user sketch
        2. Gemma 4 E4B multimodal reasoning -> SceneSpec JSON
        3. TripoSR image-to-3D reconstruction -> GLB mesh
        4. Measure timings and update job state
        """
        job = self.get_job(job_id)
        if not job:
            return

        total_start = time.time()
        job_dir = settings.GENERATED_DIR / job_id

        try:
            # Stage 1: Image Preprocessing
            self.update_job_status(
                job_id,
                JobStatus.ANALYZING,
                stage_message="Preparing sketch for reasoning..."
            )
            # Run image prep in thread
            processed_image_path = await asyncio.to_thread(
                image_service.prepare_for_inference,
                input_image_path,
                job_dir
            )
            job.processed_image_path = str(processed_image_path)

            # Stage 2: Gemma 4 E4B Multimodal Reasoning
            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} stage=gemma started")
            self.update_job_status(
                job_id,
                JobStatus.ANALYZING,
                stage_message="Analyzing sketch with Gemma 4 E4B..."
            )

            gemma_start = time.time()
            scene_spec = await asyncio.to_thread(
                gemma_service.analyze,
                processed_image_path,
                description,
                existing_spec,
                refinement_prompt
            )
            gemma_dur = time.time() - gemma_start
            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} stage=gemma completed duration={gemma_dur:.1f}s")

            job.scene_spec = scene_spec
            # Save scene_spec.json in job directory
            spec_path = safe_path_join(job_dir, "scene_spec.json")
            with open(spec_path, "w") as f:
                f.write(scene_spec.model_dump_json(indent=2))

            # Stage 3: TripoSR 3D Reconstruction
            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} stage=tripo started")
            self.update_job_status(
                job_id,
                JobStatus.GENERATING,
                stage_message="Generating 3D mesh with TripoSR..."
            )

            glb_path = safe_path_join(job_dir, "model.glb")
            tripo_start = time.time()
            await asyncio.to_thread(
                tripo_service.reconstruct,
                processed_image_path,
                glb_path,
                scene_spec
            )
            tripo_dur = time.time() - tripo_start
            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} stage=tripo completed duration={tripo_dur:.1f}s")

            # Stage 4: Completion & Packaging
            total_dur = time.time() - total_start
            job.status = JobStatus.COMPLETED
            job.stage_message = "3D reconstruction complete"
            job.model_path = str(glb_path)
            job.model_url = f"/model/{job_id}"
            job.generation_time = round(total_dur, 2)
            job.updated_at = datetime.utcnow()

            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} completed total={total_dur:.1f}s")

        except Exception as e:
            total_dur = time.time() - total_start
            logger.exception(f"Job {job_id} pipeline failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.stage_message = f"Failed: {str(e)}"
            job.updated_at = datetime.utcnow()

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Removes job storage older than max_age_hours."""
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        to_delete = []

        for job_id, job in self._jobs.items():
            if job.created_at.timestamp() < cutoff:
                to_delete.append(job_id)

        for job_id in to_delete:
            job_dir = settings.GENERATED_DIR / job_id
            if job_dir.exists():
                import shutil
                shutil.rmtree(job_dir, ignore_errors=True)
            self._jobs.pop(job_id, None)

job_service = JobService()
