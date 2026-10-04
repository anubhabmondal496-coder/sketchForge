import os
import shutil
from pathlib import Path
from PIL import Image
from fastapi import UploadFile, HTTPException

from app.config import settings
from app.utils.image_processing import safe_path_join, preprocess_sketch

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
            raise HTTPException(status_code=400, detail="Invalid image file format. Please upload PNG or JPEG.")

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

image_service = ImageService()
