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

def validate_photo_quality(image_path: Path) -> tuple[bool, str | None]:
    """
    Validates that the uploaded photo is suitable for 3D reconstruction:
    - Image can be decoded
    - Format is JPEG, PNG, or WEBP
    - Object is visible and not extremely small
    - Image is not completely blurry
    - Image contains a recognizable foreground object
    """
    if not image_path.exists():
        return False, "Uploaded image file does not exist."

    try:
        with Image.open(image_path) as img:
            img_format = (img.format or "").upper()
            if img_format not in ("JPEG", "JPG", "PNG", "WEBP"):
                return False, f"Unsupported image format: {img_format}. Supported formats are JPG, JPEG, PNG, WEBP."

            width, height = img.size
            if width < 48 or height < 48:
                return False, "The object is difficult to identify from this image. Try a clearer photo with the complete object visible."

            # Convert to RGB and grayscale for structural variance analysis
            rgb = img.convert("RGB")
            gray = rgb.convert("L")
            arr = np.array(gray, dtype=np.float32)

            # 1. Contrast / variance check (detect solid or blank images)
            std_dev = float(np.std(arr))
            if std_dev < 10.0:
                return False, "The object is difficult to identify from this image. Try a clearer photo with the complete object visible."

            # 2. Sharpness / blurriness check using discrete 2D Laplacian operator
            # L = I[1:-1, 2:] + I[1:-1, :-2] + I[2:, 1:-1] + I[:-2, 1:-1] - 4*I[1:-1, 1:-1]
            if arr.shape[0] >= 3 and arr.shape[1] >= 3:
                laplacian = (
                    arr[1:-1, 2:]
                    + arr[1:-1, :-2]
                    + arr[2:, 1:-1]
                    + arr[:-2, 1:-1]
                    - 4.0 * arr[1:-1, 1:-1]
                )
                lap_var = float(np.var(laplacian))
                # Severe blur threshold
                if lap_var < 8.0:
                    return False, "The object is difficult to identify from this image. Try a clearer photo with the complete object visible."

            # 3. Foreground visibility check:
            # Estimate background from borders, check if recognizable foreground exists
            border_pixels = np.concatenate([
                arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]
            ])
            bg_est = float(np.median(border_pixels))
            fg_diff = np.abs(arr - bg_est)
            fg_pixels = np.sum(fg_diff > 25.0)
            total_pixels = arr.shape[0] * arr.shape[1]
            fg_ratio = float(fg_pixels) / float(total_pixels)

            # If foreground object is tiny (< 1.5% of pixels) or virtually non-existent
            if fg_ratio < 0.015 and std_dev < 20.0:
                return False, "The object is difficult to identify from this image. Try a clearer photo with the complete object visible."

    except Exception:
        return False, "The object is difficult to identify from this image. Try a clearer photo with the complete object visible."

    return True, None

def preprocess_photo(
    input_path: Path,
    output_path: Path,
    target_size: int = 512,
    padding: int = 24
) -> Path:
    """
    Preprocesses a real-world reference photo for Gemma visual reasoning and 3D reconstruction:
    - Normalizes orientation (EXIF)
    - Preserves realistic colors, textures, and lighting
    - Composites any alpha transparency onto clean neutral background
    - Scales thumbnail preserving aspect ratio
    - Centers in target square canvas
    """
    with Image.open(input_path) as raw_img:
        # Respect EXIF orientation if available
        img = ImageOps.exif_transpose(raw_img)
        
        # Handle RGBA transparency
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            bg = Image.new("RGBA", img_rgba.size, (245, 245, 245, 255))
            composite = Image.alpha_composite(bg, img_rgba).convert("RGB")
        else:
            composite = img.convert("RGB")

        # Scale down to fit within (target_size - 2*padding) preserving aspect ratio
        max_dim = target_size - (2 * padding)
        composite.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Create final target canvas with neutral background
        final_img = Image.new("RGB", (target_size, target_size), (248, 249, 250))
        paste_x = (target_size - composite.width) // 2
        paste_y = (target_size - composite.height) // 2
        final_img.paste(composite, (paste_x, paste_y))

        # Ensure parent output directory exists and save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(output_path, format="PNG")

    return output_path
