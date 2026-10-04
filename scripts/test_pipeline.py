#!/usr/bin/env python3
"""
End-to-end integration test for the SketchForge pipeline:
Sketch Image -> Gemma 4 E4B Reasoning -> SceneSpec -> TripoSR 3D Mesh -> GLB Export
"""

import sys
import os
import time
from pathlib import Path
from PIL import Image, ImageDraw

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.utils.image_processing import preprocess_sketch
from app.services.gemma_service import gemma_service
from app.services.tripo_service import tripo_service

def create_sample_sketch(output_path: Path):
    """Draws a simple synthetic chair sketch for automated pipeline testing."""
    img = Image.new("RGB", (512, 512), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw chair seat
    draw.rectangle([160, 260, 350, 280], fill="black")
    # Draw chair backrest
    draw.rectangle([160, 140, 180, 260], fill="black")
    draw.rectangle([160, 140, 350, 160], fill="black")
    draw.rectangle([330, 140, 350, 260], fill="black")
    # Draw 4 legs
    draw.rectangle([170, 280, 185, 420], fill="black")
    draw.rectangle([210, 280, 225, 400], fill="black")
    draw.rectangle([285, 280, 300, 400], fill="black")
    draw.rectangle([325, 280, 340, 420], fill="black")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path

def main():
    print("=" * 65)
    print("SketchForge Pipeline Integration Test")
    print(f"Device: {settings.DEVICE}")
    print(f"Mock Mode: {settings.MOCK_MODE}")
    print("=" * 65)

    test_dir = ROOT_DIR / "backend" / "generated" / "test_run"
    test_dir.mkdir(parents=True, exist_ok=True)

    sketch_path = test_dir / "input_sketch.png"
    processed_path = test_dir / "processed_sketch.png"
    output_glb = test_dir / "output_model.glb"

    # Step 1: Create sample sketch
    print("[1/5] Preparing sample sketch...")
    create_sample_sketch(sketch_path)
    print(f"Sample sketch saved: {sketch_path}")

    # Step 2: Preprocess sketch
    print("[2/5] Preprocessing sketch...")
    preprocess_sketch(sketch_path, processed_path, target_size=512)
    assert processed_path.exists(), "Processed image must exist"
    print(f"Preprocessed sketch saved: {processed_path}")

    # Step 3: Run Gemma multimodal analysis
    print("[3/5] Running Gemma 4 E4B multimodal reasoning...")
    t0 = time.time()
    spec = gemma_service.analyze(
        image_path=processed_path,
        description="A simple wooden chair with four legs and a slatted backrest."
    )
    gemma_duration = time.time() - t0
    print(f"Gemma completed in {gemma_duration:.2f}s")
    print(f"SceneSpec Object: {spec.object} (confidence: {spec.confidence})")
    print(f"SceneSpec Style: {spec.style}")
    print(f"SceneSpec Components: {spec.components}")
    print(f"SceneSpec Geometry: {spec.geometry}")
    assert spec.object is not None, "SceneSpec must have an identified object"

    # Step 4: Run TripoSR 3D reconstruction
    print("[4/5] Running TripoSR image-to-3D mesh reconstruction...")
    t1 = time.time()
    result_path = tripo_service.reconstruct(
        image_path=processed_path,
        output_glb_path=output_glb,
        scene_spec=spec
    )
    tripo_duration = time.time() - t1
    print(f"TripoSR completed in {tripo_duration:.2f}s")

    # Step 5: Validate GLB artifact
    print("[5/5] Validating resulting GLB artifact...")
    assert result_path.exists(), f"GLB output file must exist at {result_path}"
    file_size = result_path.stat().st_size
    assert file_size > 500, f"GLB file size ({file_size} bytes) is suspiciously small"

    total_time = gemma_duration + tripo_duration
    print("=" * 65)
    print("PIPELINE TEST PASSED!")
    print(f"Total pipeline execution time: {total_time:.2f}s")
    print(f"Output GLB Path: {result_path}")
    print(f"Output GLB Size: {file_size / 1024:.1f} KB")
    print("=" * 65)

if __name__ == "__main__":
    main()
