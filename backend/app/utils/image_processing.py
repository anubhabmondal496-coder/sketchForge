import os
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
import numpy as np

def safe_path_join(base_dir: Path, *paths: str) -> Path:
    """
    Prevents path traversal attacks by validating that the resolved target path
    is strictly within the expected base directory.
    """
    base_resolved = base_dir.resolve()
    target_path = base_resolved.joinpath(*paths).resolve()
    if not str(target_path).startswith(str(base_resolved)):
        raise ValueError(f"Path traversal detected: {target_path} is outside {base_resolved}")
    return target_path

def preprocess_sketch(
    input_path: Path,
    output_path: Path,
    target_size: int = 512,
    padding: int = 32,
    enhance_contrast: bool = True
) -> Path:
    """
    Preprocesses a raw user sketch for TripoSR and Gemma 4:
    - Normalizes background to pure white / transparent
    - Boosts stroke contrast
    - Centers the drawing with appropriate boundary padding
    - Preserves the original file untouched
    """
    with Image.open(input_path) as img:
        # Convert to RGBA
        img = img.convert("RGBA")
        
        # Split channels
        r, g, b, a = img.split()
        
        # If the image is on a light or white background with alpha, composite onto white
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(background, img)
        
        # Convert to Grayscale to detect stroke bounding box
        gray = composite.convert("L")
        
        # Invert so strokes are bright (non-zero) on black background
        inverted = ImageOps.invert(gray)
        
        # Auto-threshold to find real strokes
        thresholded = inverted.point(lambda p: 255 if p > 30 else 0)
        bbox = thresholded.getbbox()
        
        if bbox:
            # Crop to detected stroke boundaries
            cropped = composite.crop(bbox)
        else:
            cropped = composite

        # Scale down to fit within (target_size - 2*padding) preserving aspect ratio
        max_dim = target_size - (2 * padding)
        cropped.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
        # Create final target canvas with white background
        final_img = Image.new("RGB", (target_size, target_size), (255, 255, 255))
        paste_x = (target_size - cropped.width) // 2
        paste_y = (target_size - cropped.height) // 2
        
        final_img.paste(cropped.convert("RGB"), (paste_x, paste_y))
        
        # Optional contrast normalization for crisp silhouette
        if enhance_contrast:
            # Mild contrast stretch
            final_img = ImageOps.autocontrast(final_img, cutoff=2)
            
        # Ensure parent output directory exists and save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(output_path, format="PNG")
        
    return output_path
