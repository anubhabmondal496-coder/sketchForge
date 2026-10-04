import pytest
from app.models.scene_spec import SceneSpec, SceneGeometry
from app.utils.validation import extract_json_from_text, validate_and_parse_scene_spec

def test_scene_spec_validation():
    valid_data = {
        "object": "chair",
        "confidence": 0.92,
        "style": "minimalist wooden",
        "material": "oak",
        "components": ["seat", "backrest", "four legs"],
        "geometry": {
            "width": 0.5,
            "depth": 0.45,
            "height": 0.9,
            "back_height": 0.8
        },
        "generation_prompt": "A simple oak chair."
    }
    spec = SceneSpec.model_validate(valid_data)
    assert spec.object == "chair"
    assert spec.confidence == 0.92
    assert spec.geometry.width == 0.5
    assert len(spec.components) == 3

def test_extract_json_from_markdown():
    markdown_output = """
    Here is the multimodal analysis for your drawing:
    ```json
    {
      "object": "lamp",
      "confidence": 0.88,
      "style": "modern",
      "material": "brass"
    }
    ```
    I hope this helps!
    """
    extracted = extract_json_from_text(markdown_output)
    assert extracted is not None
    assert extracted["object"] == "lamp"
    assert extracted["material"] == "brass"

def test_malformed_json_fallback():
    raw = "I cannot identify this drawing as a 3D geometry."
    spec, error = validate_and_parse_scene_spec(raw)
    assert spec is None
    assert error is not None
