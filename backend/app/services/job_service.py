import os
import time
import uuid
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models.job import Job, JobStatus, InputType, CreationInput
from app.models.scene_spec import SceneSpec
from app.models.asset import AssetMetadata, AssetSearchResult
from app.services.gemma_service import gemma_service
from app.services.tripo_service import tripo_service
from app.services.image_service import image_service
from app.services.asset_search_service import asset_search_service
from app.services.asset_download_service import asset_download_service
from app.utils.image_processing import safe_path_join

logger = logging.getLogger("sketchforge.jobs")

class JobService:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(
        self,
        description: Optional[str] = None,
        refinement_prompt: Optional[str] = None,
        input_type: InputType = InputType.SKETCH
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
            refinement_prompt=refinement_prompt,
            input_type=input_type
        )
        self._jobs[job_id] = job
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] job={job_id} created status=queued input_type={input_type.value}")
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
        refinement_prompt: Optional[str] = None,
        input_type: InputType = InputType.SKETCH
    ):
        """
        Executes the shared SketchForge generation pipeline asynchronously for both
        sketch and reference photo inputs:
        1. Preprocess input (sketch normalization or photo contrast/scale preservation)
        2. Gemma 4 E4B Prompting Agent multimodal reasoning -> Object understanding & queries
        3. Multi-provider 3D asset search & automatic legal import
        4. TripoSR image-to-3D reconstruction fallback -> GLB mesh
        5. Measure timings and update job state
        """
        job = self.get_job(job_id)
        if not job:
            return

        total_start = time.time()
        job_dir = settings.GENERATED_DIR / job_id

        try:
            # Stage 1: Image Preprocessing
            initial_stage_msg = "Analyzing photo..." if input_type == InputType.PHOTO else "Understanding your sketch..."
            self.update_job_status(
                job_id,
                JobStatus.ANALYZING,
                stage_message=initial_stage_msg
            )
            # Run image prep in thread based on input type
            if input_type == InputType.PHOTO:
                processed_image_path = await asyncio.to_thread(
                    image_service.prepare_photo_for_inference,
                    input_image_path,
                    job_dir
                )
            else:
                processed_image_path = await asyncio.to_thread(
                    image_service.prepare_for_inference,
                    input_image_path,
                    job_dir
                )
            job.processed_image_path = str(processed_image_path)

            # Stage 2: Prompting Agent Multimodal Reasoning & Understanding
            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} stage=gemma started (input_type={input_type.value})")
            self.update_job_status(
                job_id,
                JobStatus.ANALYZING,
                stage_message="Understanding object..."
            )

            # Step 1: Visual reasoning & search query generation
            if input_type == InputType.PHOTO:
                gemma_analysis = await asyncio.to_thread(
                    gemma_service.analyze_photo_understanding,
                    processed_image_path,
                    description
                )
            else:
                gemma_analysis = await asyncio.to_thread(
                    gemma_service.analyze_sketch_understanding,
                    processed_image_path,
                    description
                )

            job.detected_objects = gemma_analysis.detected_objects
            job.needs_clarification = gemma_analysis.needs_clarification
            job.clarification_question = gemma_analysis.clarification_question

            # If multiple objects require user clarification
            if gemma_analysis.needs_clarification:
                clarif_q = gemma_analysis.clarification_question or "I found multiple objects. Which one should I create?"
                self.update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    stage_message=clarif_q,
                    error=clarif_q
                )
                return

            logger.info(f"[{now_str}] job={job_id} Prompting Agent analysis: object={gemma_analysis.object_type}, terms={gemma_analysis.search_terms}")

            # Also generate SceneSpec for geometry fallback/refinement
            scene_spec = await asyncio.to_thread(
                gemma_service.analyze,
                processed_image_path,
                description,
                existing_spec,
                refinement_prompt
            )
            job.scene_spec = scene_spec

            spec_path = safe_path_join(job_dir, "scene_spec.json")
            with open(spec_path, "w") as f:
                f.write(scene_spec.model_dump_json(indent=2))

            # Stage 3: Asset Search Orchestrator (Steps 2, 3, 4, 9)
            asset_imported = False
            glb_path = safe_path_join(job_dir, "model.glb")

            # Only do asset search on new initial queries (not purely geometric refinement)
            if settings.ASSET_SEARCH_ENABLED and not refinement_prompt:
                self.update_job_status(
                    job_id,
                    JobStatus.SEARCHING,
                    stage_message="Searching 3D assets across providers..."
                )

                # Search across all available legal providers
                search_results = await asset_search_service.search_all(
                    object_type=gemma_analysis.object_type,
                    search_terms=gemma_analysis.search_terms,
                    features=gemma_analysis.features,
                    style=gemma_analysis.style,
                    limit_per_provider=6
                )
                job.search_results = search_results

                # Check best match
                if search_results:
                    best = search_results[0]
                    logger.info(f"[{now_str}] job={job_id} Best asset found: '{best.name}' from {best.provider} (score: {best.score})")

                    if settings.ASSET_AUTO_IMPORT and best.downloadable and best.score >= settings.ASSET_MATCH_THRESHOLD:
                        self.update_job_status(
                            job_id,
                            JobStatus.FOUND,
                            stage_message=f"Best matching model found: '{best.name}'"
                        )
                        self.update_job_status(
                            job_id,
                            JobStatus.DOWNLOADING,
                            stage_message=f"Preparing model from {best.provider}..."
                        )

                        # Resolve download URL if needed
                        dl_url = best.download_url
                        if not dl_url:
                            provider_inst = asset_search_service.get_provider(best.provider)
                            if provider_inst:
                                dl_url = await provider_inst.get_download_url(best.id)

                        if dl_url:
                            try:
                                self.update_job_status(
                                    job_id,
                                    JobStatus.IMPORTING,
                                    stage_message="Loading model into workspace..."
                                )
                                downloaded_glb = await asset_download_service.download_and_cache(
                                    url=dl_url,
                                    provider=best.provider,
                                    asset_id=best.id,
                                    metadata=best.metadata or AssetMetadata(
                                        source=best.provider,
                                        provider=best.provider,
                                        asset_id=best.id,
                                        author=best.author,
                                        license=best.license,
                                        source_url=best.preview_url or "",
                                        attribution=best.attribution or ""
                                    )
                                )
                                # Copy into job_dir model.glb
                                import shutil
                                shutil.copyfile(downloaded_glb, glb_path)
                                job.source_type = "asset_search"
                                job.asset_metadata = best.metadata
                                asset_imported = True
                                logger.info(f"[{now_str}] job={job_id} Asset {best.id} successfully imported into workspace.")
                            except Exception as import_err:
                                logger.warning(f"Could not import best asset: {import_err}. Falling back to AI 3D generation.")

            # Stage 4: AI 3D Generation Fallback (Step 6, 10)
            if not asset_imported:
                if settings.ASSET_SEARCH_ENABLED and not refinement_prompt:
                    self.update_job_status(
                        job_id,
                        JobStatus.GENERATING,
                        stage_message="No suitable asset found. Generating a new model..."
                    )
                else:
                    self.update_job_status(
                        job_id,
                        JobStatus.GENERATING,
                        stage_message="Generating 3D mesh with TripoSR..."
                    )

                tripo_start = time.time()
                await asyncio.to_thread(
                    tripo_service.reconstruct,
                    processed_image_path,
                    glb_path,
                    scene_spec
                )
                tripo_dur = time.time() - tripo_start
                job.source_type = "ai_generation"
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] job={job_id} stage=tripo completed duration={tripo_dur:.1f}s")

            # Stage 5: Completion & Packaging
            total_dur = time.time() - total_start
            job.status = JobStatus.COMPLETED
            job.stage_message = "Model ready."
            job.model_path = str(glb_path)
            job.model_url = f"/model/{job_id}"
            job.generation_time = round(total_dur, 2)
            job.updated_at = datetime.utcnow()

            now_str = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{now_str}] job={job_id} completed total={total_dur:.1f}s (source: {job.source_type})")

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
