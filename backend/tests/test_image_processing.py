import pytest
from pathlib import Path
from PIL import Image, ImageDraw
from app.utils.image_processing import safe_path_join, preprocess_sketch

def test_safe_path_join():
    base = Path("c:/Users/ANUBHAB/Desktop/SketchForge/backend/generated").resolve()
    valid = safe_path_join(base, "job_123", "model.glb")
    assert str(valid).startswith(str(base))

    # Path traversal attack detection
    with pytest.raises(ValueError):
        safe_path_join(base, "..", "..", "windows", "system32")

def test_preprocess_sketch(tmp_path):
    input_file = tmp_path / "raw_sketch.png"
    output_file = tmp_path / "processed_sketch.png"

    # Create dummy white canvas with black cross
    img = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.line([(50, 50), (200, 200)], fill=(0, 0, 0, 255), width=4)
    img.save(input_file)

    preprocess_sketch(input_file, output_file, target_size=512)
    assert output_file.exists()

    with Image.open(output_file) as processed:
        assert processed.size == (512, 512)
        assert processed.mode == "RGB"
