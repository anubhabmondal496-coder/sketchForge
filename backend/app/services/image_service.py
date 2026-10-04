import os
import shutil
from pathlib import Path
from PIL import Image
from fastapi import UploadFile, HTTPException

from app.config import settings
from app.utils.image_processing import (
    safe_path_join,
    preprocess_sketch,
    preprocess_photo,
    validate_photo_quality,
)

class ImageService:
    @staticmethod
    async def save_uploaded_sketch(upload_file: UploadFile, job_dir: Path) -> Path:
        """
        Validates and saves the incoming uploaded sketch file into the job directory.
        """
        input_path = safe_path_join(job_dir, "input.png")
        
        # Read and check file content
        content = await upload_file.read()
        if not content or len(content) < 64:
            raise HTTPException(status_code=400, detail="Uploaded image file is empty or corrupted.")

        # Write to disk
        with open(input_path, "wb") as f:
            f.write(content)

        # Validate with PIL
        try:
            with Image.open(input_path) as img:
                img.verify()
        except Exception:
            if input_path.exists():
                input_path.unlink()
            raise HTTPException(status_code=400, detail="Invalid image file format. Supported formats are JPG, JPEG, PNG, WEBP.")

        return input_path

    @staticmethod
    async def save_uploaded_photo(upload_file: UploadFile, job_dir: Path) -> Path:
        """
        Validates, saves, and quality-checks the incoming reference photo.
        Enforces size limit (10MB), supported formats (JPG, JPEG, PNG, WEBP),
        and verifies object clarity / recognizability.
        """
        max_bytes = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
        content = await upload_file.read()
        if not content or len(content) < 64:
            raise HTTPException(status_code=400, detail="Uploaded image file is empty or corrupted.")

        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Image size ({len(content) / (1024 * 1024):.1f} MB) exceeds the {settings.MAX_PHOTO_SIZE_MB} MB limit. Please upload a smaller image."
            )

        # 1. Format & Decode verification with PIL on raw byte stream
        import io
        try:
            with Image.open(io.BytesIO(content)) as probe:
                img_format = (probe.format or "").upper()
                if img_format not in ("JPEG", "JPG", "PNG", "WEBP"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported image format: {img_format}. Supported formats are JPG, JPEG, PNG, WEBP."
                    )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Uploaded image is corrupted and cannot be decoded.")

        # Determine target extension from verified image format
        ext = ".png" if img_format == "PNG" else (".webp" if img_format == "WEBP" else ".jpg")
        input_path = safe_path_join(job_dir, f"input_photo{ext}")

        with open(input_path, "wb") as f:
            f.write(content)

        # 2. Quality & Object Visibility Check
        is_ok, quality_error = validate_photo_quality(input_path)
        if not is_ok:
            if input_path.exists():
                input_path.unlink()
            raise HTTPException(status_code=400, detail=quality_error or "The object is difficult to identify from this image. Try a clearer photo with the complete object visible.")

        return input_path

    @staticmethod
    def prepare_for_inference(input_path: Path, job_dir: Path) -> Path:
        """
        Preprocesses sketch for multimodal analysis and 3D reconstruction.
        """
        processed_path = safe_path_join(job_dir, "processed.png")
        preprocess_sketch(
            input_path=input_path,
            output_path=processed_path,
            target_size=512,
            padding=32,
            enhance_contrast=True
        )
        return processed_path

    @staticmethod
    def prepare_photo_for_inference(input_path: Path, job_dir: Path) -> Path:
        """
        Preprocesses reference photo for multimodal analysis and 3D reconstruction.
        """
        processed_path = safe_path_join(job_dir, "processed.png")
        preprocess_photo(
            input_path=input_path,
            output_path=processed_path,
            target_size=512,
            padding=24
        )
        return processed_path

image_service = ImageService()
