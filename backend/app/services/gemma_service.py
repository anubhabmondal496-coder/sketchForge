import os
import time
import logging
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image

import torch
from app.config import settings
from app.models.scene_spec import SceneSpec, SceneGeometry
from app.utils.validation import validate_and_parse_scene_spec

logger = logging.getLogger("sketchforge.gemma")

SYSTEM_PROMPT = """You are the visual reasoning and geometry planning engine for SketchForge.
Your task is to analyze a 2D sketch of an object and optional user description, and output a strict structured SceneSpec JSON.
You must output ONLY valid JSON. Do not output conversational prose or explanations.

The JSON schema must strictly conform to:
{
  "object": "name of object (e.g. chair, mug, table, lamp, vase)",
  "confidence": 0.92,
  "style": "aesthetic description (e.g. minimalist wooden, modern ceramic)",
  "material": "primary material (e.g. oak wood, polished porcelain, brushed steel)",
  "components": ["list", "of", "detected", "parts"],
  "geometry": {
    "width": 0.5,
    "depth": 0.45,
    "height": 0.9,
    "back_height": 0.8
  },
  "generation_prompt": "A complete, high-fidelity description tailored for 3D reconstruction"
}
"""

class GemmaService:
    def __init__(self):
        self._processor = None
        self._model = None
        self._loaded = False

    def is_available(self) -> bool:
        if settings.MOCK_MODE:
            return True
        return torch.cuda.is_available() or settings.DEVICE == "cpu"

    def get_model(self):
        """
        Lazy-loads Gemma 4 E4B using official Hugging Face Transformers multimodal pipeline.
        """
        if self._loaded and self._model is not None:
            return self._processor, self._model

        if settings.MOCK_MODE:
            logger.info("GemmaService: Running in MOCK_MODE, skipping weight download.")
            self._loaded = True
            return None, None

        logger.info(f"Loading Gemma 4 E4B model: {settings.GEMMA_MODEL_ID}")
        start_time = time.time()

        from transformers import AutoProcessor

        model_kwargs = {
            "cache_dir": settings.MODEL_CACHE_DIR,
            "token": settings.HF_TOKEN if settings.HF_TOKEN else None,
        }

        # Select target device & quantization
        device = "cuda" if torch.cuda.is_available() and settings.DEVICE == "cuda" else "cpu"

        if device == "cuda" and settings.LOAD_IN_4BIT:
            try:
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                model_kwargs["quantization_config"] = quantization_config
                model_kwargs["device_map"] = "auto"
            except Exception as e:
                logger.warning(f"4-bit quantization config failed: {e}. Falling back to standard device map.")
                model_kwargs["device_map"] = "auto"
        elif device == "cuda":
            model_kwargs["torch_dtype"] = torch.float16
            model_kwargs["device_map"] = "auto"
        else:
            model_kwargs["torch_dtype"] = torch.float32

        # Try multimodal model classes
        try:
            from transformers import AutoModelForMultimodalLM
            model_cls = AutoModelForMultimodalLM
        except ImportError:
            try:
                from transformers import AutoModelForImageTextToText
                model_cls = AutoModelForImageTextToText
            except ImportError:
                from transformers import AutoModelForVision2Seq
                model_cls = AutoModelForVision2Seq

        self._processor = AutoProcessor.from_pretrained(settings.GEMMA_MODEL_ID, **model_kwargs)
        self._model = model_cls.from_pretrained(settings.GEMMA_MODEL_ID, **model_kwargs)
        self._loaded = True

        load_duration = time.time() - start_time
        logger.info(f"Gemma 4 loaded successfully in {load_duration:.2f}s on {device}")
        return self._processor, self._model

    def unload_model(self):
        """Unload model from VRAM to preserve GPU memory."""
        if self._model is not None:
            del self._model
            del self._processor
            self._model = None
            self._processor = None
            self._loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Gemma model unloaded and GPU VRAM cache cleared.")

    def analyze(
        self,
        image_path: Path,
        description: Optional[str] = None,
        existing_spec: Optional[SceneSpec] = None,
        refinement_prompt: Optional[str] = None
    ) -> SceneSpec:
        """
        Runs multimodal inference with Gemma 4 E4B to produce a strict SceneSpec JSON.
        """
        start_time = time.time()
        logger.info(f"Gemma analysis started. Image: {image_path}, Description: {description}")

        # Check for Mock Mode or offline fallback
        if settings.MOCK_MODE or not torch.cuda.is_available():
            spec = self._generate_mock_spec(description, existing_spec, refinement_prompt)
            duration = time.time() - start_time
            logger.info(f"Gemma mock inference completed in {duration:.2f}s")
            return spec

        try:
            processor, model = self.get_model()
            
            # Prepare multimodal prompt
            user_text_parts = []
            if existing_spec and refinement_prompt:
                user_text_parts.append(
                    f"Existing SceneSpec: {existing_spec.model_dump_json()}\n"
                    f"Refinement instructions: {refinement_prompt}\n"
                    f"Update the SceneSpec geometry, components, and material according to the instructions."
                )
            else:
                if description:
                    user_text_parts.append(f"User description: {description.strip()}")
                user_text_parts.append("Examine the attached sketch. Output the complete SceneSpec JSON.")

            user_content = "\n".join(user_text_parts)

            image = Image.open(image_path).convert("RGB")
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": user_content}
                    ]
                }
            ]

            # Format with processor chat template
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt"
            )

            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.2,
                    do_sample=False
                )

            # Slice out generated response tokens
            input_len = inputs["input_ids"].shape[-1]
            generated_ids = outputs[0][input_len:]
            raw_text = processor.decode(generated_ids, skip_special_tokens=True)

            # Validate and parse JSON
            spec, error = validate_and_parse_scene_spec(raw_text)

            # If malformed, retry once with explicit correction prompt
            if not spec:
                logger.warning(f"Initial Gemma JSON malformed ({error}). Retrying with correction prompt.")
                retry_messages = messages + [
                    {"role": "assistant", "content": raw_text},
                    {"role": "user", "content": f"Your output had formatting errors: {error}. Return ONLY the valid JSON block conforming to SceneSpec."}
                ]
                retry_inputs = processor.apply_chat_template(
                    retry_messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt"
                )
                retry_inputs = {k: v.to(device) for k, v in retry_inputs.items()}
                with torch.no_grad():
                    retry_outputs = model.generate(**retry_inputs, max_new_tokens=512, temperature=0.1)
                retry_text = processor.decode(retry_outputs[0][retry_inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
                spec, retry_error = validate_and_parse_scene_spec(retry_text)

            if not spec:
                logger.error(f"Failed to produce valid SceneSpec after retry: {error}")
                # Safe fallback to prevent pipeline crash
                spec = self._generate_mock_spec(description, existing_spec, refinement_prompt)

            duration = time.time() - start_time
            logger.info(f"Gemma inference completed in {duration:.2f}s. Spec object: {spec.object}")
            return spec

        except Exception as e:
            logger.exception(f"Gemma inference error: {e}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return self._generate_mock_spec(description, existing_spec, refinement_prompt)

    def _generate_mock_spec(
        self,
        description: Optional[str] = None,
        existing_spec: Optional[SceneSpec] = None,
        refinement_prompt: Optional[str] = None
    ) -> SceneSpec:
        """
        Deterministic, intelligent SceneSpec generation for development / mock mode.
        """
        # If refining an existing spec
        if existing_spec and refinement_prompt:
            p_lower = refinement_prompt.lower()
            new_spec = existing_spec.model_copy(deep=True)
            if not new_spec.geometry:
                new_spec.geometry = SceneGeometry()

            if "taller" in p_lower or "longer" in p_lower:
                new_spec.geometry.height = (new_spec.geometry.height or 0.9) * 1.3
                if new_spec.geometry.back_height:
                    new_spec.geometry.back_height *= 1.35
            if "wider" in p_lower:
                new_spec.geometry.width = (new_spec.geometry.width or 0.5) * 1.3
            if "armrest" in p_lower:
                if "armrests" not in new_spec.components:
                    new_spec.components.append("armrests")
            if "metallic" in p_lower or "metal" in p_lower:
                new_spec.material = "brushed aluminum metal"
            if "wood" in p_lower:
                new_spec.material = "polished oak wood"

            new_spec.generation_prompt = f"{existing_spec.generation_prompt or existing_spec.object}, refined with: {refinement_prompt}"
            return new_spec

        # Detect object category from description
        desc_lower = (description or "").lower()
        if "table" in desc_lower:
            return SceneSpec(
                object="table",
                confidence=0.94,
                style="modern minimalist",
                material="natural oak wood",
                components=["tabletop plane", "four cylindrical legs", "reinforcement aprons"],
                geometry=SceneGeometry(width=1.2, depth=0.8, height=0.75),
                generation_prompt="A modern dining table with a thick oak surface and four sturdy tapered legs."
            )
        elif "lamp" in desc_lower:
            return SceneSpec(
                object="lamp",
                confidence=0.91,
                style="contemporary studio",
                material="frosted glass and brass",
                components=["cylindrical lampshade", "slender brass stem", "circular weighted base"],
                geometry=SceneGeometry(width=0.35, depth=0.35, height=0.6),
                generation_prompt="A minimalist studio bedside lamp with a warm frosted shade and brass base."
            )
        elif "mug" in desc_lower or "cup" in desc_lower:
            return SceneSpec(
                object="mug",
                confidence=0.93,
                style="artisan ceramic",
                material="matte stoneware ceramic",
                components=["cylindrical cup body", "curved ergonomic handle", "reinforced base rim"],
                geometry=SceneGeometry(width=0.12, depth=0.09, height=0.1),
                generation_prompt="A ceramic stoneware coffee mug with smooth matte glaze and ergonomic loop handle."
            )
        else:
            # Default object: chair
            return SceneSpec(
                object="chair",
                confidence=0.92,
                style="simple wooden craftsmanship",
                material="scandinavian beech wood",
                components=["seat cushion", "slatted backrest", "four legs", "leg stretchers"],
                geometry=SceneGeometry(width=0.5, depth=0.48, height=0.92, back_height=0.85),
                generation_prompt="A handcrafted wooden chair with four tapered legs and a tall slatted backrest."
            )

gemma_service = GemmaService()
