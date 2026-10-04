import json
import re
from typing import Optional, Tuple
from app.models.scene_spec import SceneSpec, SceneGeometry

def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Safely extracts a JSON object from text that may contain markdown formatting,
    fenced code blocks, or explanatory commentary.
    """
    if not text:
        return None
        
    text_clean = text.strip()
    
    # 1. Check for standard markdown json code block
    json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_clean, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1))
        except json.JSONDecodeError:
            pass
            
    # 2. Check for outermost balanced curly braces
    brace_match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass
            
    # 3. Direct parse attempt
    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        return None

def validate_and_parse_scene_spec(raw_output: str) -> Tuple[Optional[SceneSpec], Optional[str]]:
    """
    Validates model output string against SceneSpec Pydantic schema.
    Returns (SceneSpec, None) on success or (None, error_message) on failure.
    """
    extracted_dict = extract_json_from_text(raw_output)
    if not extracted_dict:
        return None, "No valid JSON structure found in model reasoning output."
        
    try:
        # Normalize fields if necessary
        if "object" not in extracted_dict or not str(extracted_dict["object"]).strip():
            extracted_dict["object"] = "object"
            
        spec = SceneSpec.model_validate(extracted_dict)
        return spec, None
    except Exception as e:
        return None, f"SceneSpec schema validation failed: {str(e)}"
