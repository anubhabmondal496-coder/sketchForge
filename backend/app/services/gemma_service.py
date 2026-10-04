import os
import time
import logging
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np

import torch
from app.config import settings
from app.models.scene_spec import SceneSpec, SceneGeometry
from app.models.asset import GemmaAnalysisResult
from app.utils.validation import validate_and_parse_scene_spec, validate_and_parse_gemma_analysis

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

GEMMA_ANALYSIS_SYSTEM_PROMPT = """You are the visual reasoning layer of SketchForge.
Your task is to examine a rough 2D sketch and optional natural language description, and identify what object the user wants.
Do NOT generate 3D geometry or mesh vertices at this stage.
Output ONLY a strict structured JSON object conforming to:
{
  "object_type": "office chair",
  "canonical_name": "office chair",
  "search_terms": [
    "office chair",
    "desk chair",
    "computer chair",
    "ergonomic chair"
  ],
  "style": [
    "modern",
    "black"
  ],
  "features": [
    "armrests",
    "five wheels",
    "high backrest"
  ],
  "approximate_scale": "human-sized",
  "confidence": 0.91
}
Do not expose chain-of-thought. Output valid JSON only.
"""

GEMMA_PHOTO_ANALYSIS_SYSTEM_PROMPT = """You are the Prompting Agent for SketchForge analyzing a reference photo for 3D reconstruction.
Your task is to understand what the user wants, inspect the photo and optional user description, and produce a structured representation for asset search and 3D generation.

Evaluate:
1. Object category and subtype.
2. Major components, visible geometry, approximate proportions, materials, colors, and style.
3. Multiple objects detection:
   - If the photo contains multiple distinct foreground objects (e.g. chair, table, laptop) and user description specifies an object (e.g. "Create the chair"), identify that specific object as the primary object.
   - If multiple distinct objects are present and the user has NOT specified which one to create, list all detected objects in "detected_objects", set "needs_clarification": true, and "clarification_question": "I found multiple objects. Which one should I create?".
4. Generate 4-6 tiered search queries for 3D asset search:
   - exact object
   - common synonym
   - object + important features
   - object + style
   - object + distinguishing characteristic
5. Do NOT expose chain-of-thought. Output valid JSON only conforming to:
{
  "object_type": "office chair",
  "canonical_name": "chair",
  "search_terms": [
    "modern office chair",
    "desk chair",
    "office chair tall backrest armrests",
    "modern ergonomic office chair",
    "black office chair"
  ],
  "style": ["modern", "ergonomic"],
  "features": ["tall backrest", "armrests", "five-wheel base"],
  "components": ["seat", "backrest", "two armrests", "central support", "five-wheel base"],
  "materials": ["fabric", "plastic", "metal"],
  "colors": ["black"],
  "user_modifications": [],
  "detected_objects": ["office chair"],
  "needs_clarification": false,
  "clarification_question": null,
  "approximate_scale": "human-sized",
  "confidence": 0.95
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
            spec = self._generate_mock_spec(image_path, description, existing_spec, refinement_prompt)
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
            return self._generate_mock_spec(image_path, description, existing_spec, refinement_prompt)

    def _analyze_image_geometry(self, image_path: Optional[Path]) -> dict:
        """
        Extracts structural geometric cues from the 2D sketch silhouette:
        - Aspect ratio (width / height)
        - 3-tier vertical mass distribution (top, middle, bottom)
        - Slender stem detection (hallmark of lamps, goblets, pedestals)
        """
        if not image_path or not image_path.exists():
            return {
                "aspect_ratio": 1.0,
                "is_wide": False,
                "is_tall": False,
                "is_lamp": False,
                "is_table": False,
                "is_mug": False,
            }

        try:
            with Image.open(image_path) as img:
                gray = img.convert("L")
                inv = ImageOps.invert(gray)
                arr = np.array(inv)
                bbox = inv.point(lambda p: 255 if p > 30 else 0).getbbox()

                if not bbox:
                    return {
                        "aspect_ratio": 1.0,
                        "is_wide": False,
                        "is_tall": False,
                        "is_lamp": False,
                        "is_table": False,
                        "is_mug": False,
                    }

                min_x, min_y, max_x, max_y = bbox
                w = max(1, max_x - min_x)
                h = max(1, max_y - min_y)
                aspect = w / h

                cropped = arr[min_y:max_y, min_x:max_x]
                ch, cw = cropped.shape
                
                # Split into 3 vertical zones: top third, middle third, bottom third
                t_end = max(1, ch // 3)
                m_end = max(2, (2 * ch) // 3)
                top_zone = cropped[:t_end, :]
                mid_zone = cropped[t_end:m_end, :]
                bot_zone = cropped[m_end:, :]

                top_m = float(top_zone.sum())
                mid_m = float(mid_zone.sum())
                bot_m = float(bot_zone.sum())
                tot_m = top_m + mid_m + bot_m + 1e-5

                top_pct = top_m / tot_m
                mid_pct = mid_m / tot_m
                bot_pct = bot_m / tot_m

                # Lamp signature: Slender center stem with prominent lampshade on top and weighted base at bottom
                # i.e., Middle zone has significantly less stroke mass than top or bottom (mid_pct <= 0.20 and top_pct >= 0.35)
                is_lamp = (mid_pct < 0.22 and top_pct > 0.35 and aspect < 1.1)

                # Table signature: Dominant wide horizontal surface (aspect > 1.25)
                is_table = (aspect > 1.25)

                # Mug signature: Compact / square aspect ratio, balanced middle mass, not slender stem
                is_mug = (0.75 <= aspect <= 1.25 and mid_pct >= 0.25 and not is_lamp)

                return {
                    "aspect_ratio": aspect,
                    "is_wide": aspect > 1.25,
                    "is_tall": aspect < 0.85,
                    "top_pct": top_pct,
                    "mid_pct": mid_pct,
                    "bot_pct": bot_pct,
                    "is_lamp": is_lamp,
                    "is_table": is_table,
                    "is_mug": is_mug,
                }
        except Exception as e:
            logger.warning(f"Error computing visual geometry heuristics: {e}")
            return {
                "aspect_ratio": 1.0,
                "is_wide": False,
                "is_tall": False,
                "is_lamp": False,
                "is_table": False,
                "is_mug": False,
            }

    def _generate_mock_spec(
        self,
        image_path: Optional[Path] = None,
        description: Optional[str] = None,
        existing_spec: Optional[SceneSpec] = None,
        refinement_prompt: Optional[str] = None
    ) -> SceneSpec:
        """
        Deterministic, intelligent SceneSpec generation using multi-modal reasoning:
        Uses both the text description and sketch silhouette geometry cues.
        """
        # If refining an existing spec
        if existing_spec and refinement_prompt:
            p_lower = refinement_prompt.lower()
            new_spec = existing_spec.model_copy(deep=True)
            if not new_spec.geometry:
                new_spec.geometry = SceneGeometry()

            if "taller" in p_lower or "longer" in p_lower:
                new_spec.geometry.height = round((new_spec.geometry.height or 0.9) * 1.3, 2)
                if new_spec.geometry.back_height:
                    new_spec.geometry.back_height = round(new_spec.geometry.back_height * 1.35, 2)
            if "wider" in p_lower:
                new_spec.geometry.width = round((new_spec.geometry.width or 0.5) * 1.3, 2)
            if "armrest" in p_lower:
                if "armrests" not in new_spec.components:
                    new_spec.components.append("armrests")
            if "metallic" in p_lower or "metal" in p_lower:
                new_spec.material = "brushed aluminum metal"
            if "wood" in p_lower:
                new_spec.material = "polished oak wood"
            if "ceramic" in p_lower or "clay" in p_lower:
                new_spec.material = "matte ceramic"

            new_spec.generation_prompt = f"{existing_spec.generation_prompt or existing_spec.object}, refined with: {refinement_prompt}"
            return new_spec

        # 1. Inspect user text prompt keywords
        desc_lower = (description or "").lower()

        # 2. Extract visual silhouette geometry features from the sketch
        geom = self._analyze_image_geometry(image_path)
        aspect = geom.get("aspect_ratio", 1.0)
        is_wide = geom.get("is_wide", False)
        is_tall = geom.get("is_tall", False)
        top_heavy = geom.get("top_heavy", False)
        bottom_heavy = geom.get("bottom_heavy", False)

        # Classify based on combination of prompt and sketch shape
        if desc_lower:
            # Extract main object noun from user description
            import re
            cleaned_desc = re.sub(r'^(a|an|the)\s+', '', desc_lower.strip())
            words = cleaned_desc.split()
            # Object name is typically the primary noun/phrase
            obj_name = words[0] if len(words) == 1 else " ".join(words[:3])

            # Determine material from prompt
            material = "standard composite"
            if any(k in desc_lower for k in ["wood", "wooden", "timber", "oak", "pine"]):
                material = "natural polished wood"
            elif any(k in desc_lower for k in ["metal", "steel", "iron", "aluminum", "metallic", "gold", "silver", "chrome"]):
                material = "brushed metallic alloy"
            elif any(k in desc_lower for k in ["glass", "crystal", "transparent"]):
                material = "translucent tempered glass"
            elif any(k in desc_lower for k in ["ceramic", "porcelain", "clay", "pottery"]):
                material = "glazed ceramic"
            elif any(k in desc_lower for k in ["plastic", "polymer", "resin"]):
                material = "matte molded polymer"
            elif any(k in desc_lower for k in ["stone", "marble", "granite", "rock"]):
                material = "cut polished marble"
            elif any(k in desc_lower for k in ["fabric", "leather", "cloth"]):
                material = "textured leather upholstery"

            # Determine style
            style = "custom artisan"
            if any(k in desc_lower for k in ["modern", "minimalist", "sleek"]):
                style = "modern minimalist"
            elif any(k in desc_lower for k in ["vintage", "retro", "classic", "antique"]):
                style = "vintage handcrafted"
            elif any(k in desc_lower for k in ["futuristic", "cyberpunk", "sci-fi"]):
                style = "futuristic geometric"

            return SceneSpec(
                object=cleaned_desc,
                confidence=0.95,
                style=style,
                material=material,
                components=[f"{cleaned_desc} primary structure", "surface boundary", "structural base"],
                geometry=SceneGeometry(
                    width=round(max(0.4, min(2.5, aspect * 0.8)), 2),
                    depth=round(max(0.3, min(2.0, aspect * 0.6)), 2),
                    height=round(max(0.4, min(2.5, 1.0 / (aspect + 1e-4) * 0.8)), 2)
                ),
                generation_prompt=f"A high-fidelity 3D model of {cleaned_desc} with {style} aesthetic and {material} finish."
            )

        # If no prompt was provided, deduce from sketch geometric cues
        if geom.get("is_lamp"):
            # Slender stem + top shade + weighted base -> Studio / Bedside Lamp
            return SceneSpec(
                object="lamp",
                confidence=0.95,
                style="contemporary studio",
                material="frosted glass and brass",
                components=["cylindrical lampshade", "slender brass stem", "circular weighted base"],
                geometry=SceneGeometry(width=0.35, depth=0.35, height=round(max(0.5, 1.0 / (aspect + 1e-4) * 0.4), 2)),
                generation_prompt="A minimalist studio bedside lamp with a warm frosted shade and brass base."
            )
        elif geom.get("is_table"):
            # Wide horizontal aspect ratio -> Table / Desk
            return SceneSpec(
                object="table",
                confidence=0.94,
                style="modern minimalist",
                material="natural oak wood",
                components=["tabletop plane", "four cylindrical legs", "reinforcement aprons"],
                geometry=SceneGeometry(width=round(max(0.8, aspect * 0.7), 2), depth=0.8, height=0.75),
                generation_prompt="A modern dining table with a thick oak surface and four sturdy tapered legs."
            )
        elif geom.get("is_mug"):
            # Compact / square with centered base -> Mug / Vessel
            return SceneSpec(
                object="mug",
                confidence=0.93,
                style="artisan ceramic",
                material="matte stoneware ceramic",
                components=["cylindrical cup body", "curved ergonomic handle", "reinforced base rim"],
                geometry=SceneGeometry(width=0.12, depth=0.09, height=0.12),
                generation_prompt="A ceramic stoneware coffee mug with smooth matte glaze and ergonomic loop handle."
            )
        else:
            # Default or tall balanced silhouette -> Chair / Seating
            return SceneSpec(
                object="chair",
                confidence=0.92,
                style="simple wooden craftsmanship",
                material="scandinavian beech wood",
                components=["seat cushion", "slatted backrest", "four legs", "leg stretchers"],
                geometry=SceneGeometry(width=0.5, depth=0.48, height=0.92, back_height=0.85),
                generation_prompt="A handcrafted wooden chair with four tapered legs and a tall slatted backrest."
            )

    def analyze_sketch_understanding(
        self,
        image_path: Optional[Path],
        description: Optional[str] = None
    ) -> GemmaAnalysisResult:
        """
        Step 1 Visual Reasoning Layer:
        Uses Gemma 4 E4B to understand the sketch and natural language description.
        Generates structured JSON describing object type, canonical name, search terms,
        style, and features without generating 3D mesh geometry.
        """
        start_time = time.time()
        logger.info(f"Gemma visual understanding started. Image: {image_path}, Description: {description}")

        # Check mock mode or no CUDA
        if settings.MOCK_MODE or not torch.cuda.is_available():
            result = self._generate_mock_analysis(image_path, description)
            logger.info(f"Gemma mock visual understanding completed in {time.time() - start_time:.2f}s")
            return result

        try:
            processor, model = self.get_model()
            user_text_parts = []
            if description:
                user_text_parts.append(f"User description: {description.strip()}")
            user_text_parts.append("Examine the attached sketch. Output the complete visual analysis JSON with normalized search terms.")

            user_content = "\n".join(user_text_parts)
            image = Image.open(image_path).convert("RGB")

            messages = [
                {"role": "system", "content": GEMMA_ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": user_content}
                    ]
                }
            ]

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
                    max_new_tokens=384,
                    temperature=0.2,
                    do_sample=False
                )

            input_len = inputs["input_ids"].shape[-1]
            generated_ids = outputs[0][input_len:]
            raw_text = processor.decode(generated_ids, skip_special_tokens=True)

            res, error = validate_and_parse_gemma_analysis(raw_text)
            if not res:
                logger.warning(f"Gemma visual understanding parse error ({error}). Falling back to heuristic analysis.")
                return self._generate_mock_analysis(image_path, description)

            return res

        except Exception as e:
            logger.warning(f"Gemma visual analysis error: {e}. Falling back to deterministic reasoning.")
            return self._generate_mock_analysis(image_path, description)

    def _generate_mock_analysis(
        self,
        image_path: Optional[Path],
        description: Optional[str] = None
    ) -> GemmaAnalysisResult:
        """
        Deterministic normalization and search term generator for Step 1.
        Converts user description & sketch silhouette into normalized search queries.
        """
        import re
        desc_lower = (description or "").lower().strip()
        geom = self._analyze_image_geometry(image_path)

        # Detect primary object
        object_type = "office chair"
        canonical = "chair"
        styles = ["modern"]
        features = ["support structure"]

        # Parse keywords from description
        if any(w in desc_lower for w in ["lamp", "light", "lantern", "desk lamp"]):
            object_type = "desk lamp"
            canonical = "lamp"
            features = ["round base", "lampshade", "slender stem"]
            styles = ["modern", "minimalist"]
        elif any(w in desc_lower for w in ["table", "desk", "dining table", "coffee table"]):
            object_type = "dining table"
            canonical = "table"
            features = ["four legs", "wooden tabletop", "support aprons"]
            styles = ["wooden", "modern"]
        elif any(w in desc_lower for w in ["chair", "office chair", "seat", "stool", "armchair"]):
            object_type = "office chair"
            canonical = "chair"
            features = ["armrests", "five wheels", "high backrest"]
            styles = ["modern", "ergonomic"]
        elif any(w in desc_lower for w in ["house", "home", "building", "cottage", "cabin", "residence", "villa"]):
            object_type = "cottage house"
            canonical = "house"
            features = ["pitched roof", "chimney", "front door", "windows"]
            styles = ["suburban", "architectural"]
        elif geom.get("is_lamp"):
            object_type = "desk lamp"
            canonical = "lamp"
            features = ["round base", "lampshade"]
        elif geom.get("is_table"):
            object_type = "table"
            canonical = "table"
            features = ["tabletop", "legs"]
        elif geom.get("is_mug"):
            object_type = "coffee mug"
            canonical = "mug"
            features = ["handle", "cup body"]
            styles = ["ceramic"]

        # Style detection from description
        if "wood" in desc_lower or "wooden" in desc_lower:
            styles.append("wooden")
        if "metal" in desc_lower or "steel" in desc_lower:
            styles.append("metal")
        if "black" in desc_lower:
            styles.append("black")
        if "white" in desc_lower:
            styles.append("white")
        if "vintage" in desc_lower:
            styles.append("vintage")

        # Feature detection from description
        if "armrest" in desc_lower:
            if "armrests" not in features:
                features.append("armrests")
        if "wheel" in desc_lower:
            if "wheels" not in features:
                features.append("wheels")
        if "tall" in desc_lower or "high" in desc_lower:
            if "high backrest" not in features and canonical == "chair":
                features.append("high backrest")
        if "round" in desc_lower:
            if "round base" not in features and canonical == "lamp":
                features.append("round base")

        # Generate normalized search terms as required in Step 3
        search_terms = []
        # 1. Combination of primary style + canonical
        for s in styles:
            search_terms.append(f"{s} {canonical}")
        # 2. Object type directly
        search_terms.append(object_type)
        # 3. Canonical + feature
        for f in features:
            search_terms.append(f"{canonical} {f}")
        # 4. Synonyms
        if canonical == "chair":
            search_terms.extend(["desk chair", "computer chair", "ergonomic chair"])
        elif canonical == "table":
            search_terms.extend(["wooden desk", "dining table", "study table"])
        elif canonical == "lamp":
            search_terms.extend(["modern lamp", "table lamp", "study light"])
        elif canonical == "house":
            search_terms.extend(["cottage house", "suburban home", "cottage building", "residential house"])

        # Deduplicate preserving order
        seen = set()
        dedup_terms = []
        for t in search_terms:
            t_clean = t.strip().lower()
            if t_clean and t_clean not in seen:
                seen.add(t_clean)
                dedup_terms.append(t_clean)

        return GemmaAnalysisResult(
            object_type=object_type,
            canonical_name=canonical,
            search_terms=dedup_terms[:6],
            style=list(set(styles)),
            features=features,
            approximate_scale="human-sized",
            confidence=0.92
        )

    def analyze_photo_understanding(
        self,
        image_path: Optional[Path],
        description: Optional[str] = None
    ) -> GemmaAnalysisResult:
        """
        Multimodal Prompting Agent layer for reference photos:
        Understands the uploaded photo, extracts components, materials, colors, features,
        and generates tiered search queries for asset search and 3D generation.
        Handles multiple objects detection and description disambiguation.
        """
        start_time = time.time()
        logger.info(f"Gemma photo understanding started. Image: {image_path}, Description: {description}")

        # Check mock mode or mock photo generation or no CUDA
        if settings.MOCK_MODE or settings.MOCK_PHOTO_GENERATION or not torch.cuda.is_available():
            result = self._generate_mock_photo_analysis(image_path, description)
            logger.info(f"Gemma mock photo understanding completed in {time.time() - start_time:.2f}s")
            return result

        try:
            processor, model = self.get_model()
            user_text_parts = []
            if description:
                user_text_parts.append(f"User description: {description.strip()}")
            user_text_parts.append("Examine the attached photo. Identify the primary object and return the structured visual analysis JSON.")

            user_content = "\n".join(user_text_parts)
            image = Image.open(image_path).convert("RGB")

            messages = [
                {"role": "system", "content": GEMMA_PHOTO_ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": user_content}
                    ]
                }
            ]

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
                    max_new_tokens=400,
                    temperature=0.2,
                    do_sample=False
                )

            input_len = inputs["input_ids"].shape[-1]
            generated_ids = outputs[0][input_len:]
            raw_text = processor.decode(generated_ids, skip_special_tokens=True)

            res, error = validate_and_parse_gemma_analysis(raw_text)
            if not res:
                logger.warning(f"Gemma photo understanding parse error ({error}). Falling back to deterministic analysis.")
                return self._generate_mock_photo_analysis(image_path, description)

            return res

        except Exception as e:
            logger.warning(f"Gemma photo analysis error: {e}. Falling back to deterministic analysis.")
            return self._generate_mock_photo_analysis(image_path, description)

    def _generate_mock_photo_analysis(
        self,
        image_path: Optional[Path],
        description: Optional[str] = None
    ) -> GemmaAnalysisResult:
        """
        Deterministic, intelligent Prompting Agent reasoning for uploaded photos:
        - Resolves primary object vs multiple objects
        - Honors user description constraints (e.g. "Create the chair")
        - Decomposes object into components, materials, colors, and features
        - Generates 5 tiered search queries
        """
        desc_lower = (description or "").lower().strip()
        geom = self._analyze_image_geometry(image_path)

        # 1. Check for multiple objects in photo or description
        possible_items = [
            ("chair", "office chair"),
            ("table", "dining table"),
            ("lamp", "desk lamp"),
            ("laptop", "laptop computer"),
            ("mug", "ceramic mug"),
        ]

        found_in_desc = [canon for canon, full in possible_items if canon in desc_lower]

        # Explicit user selection target
        explicit_target = None
        for canon, full in possible_items:
            if f"create the {canon}" in desc_lower or f"make the {canon}" in desc_lower or f"only the {canon}" in desc_lower:
                explicit_target = canon
                break

        # Check if multiple objects without clear single selection
        if len(found_in_desc) > 1 and not explicit_target:
            return GemmaAnalysisResult(
                object_type=found_in_desc[0],
                canonical_name=found_in_desc[0],
                search_terms=[f"modern {o}" for o in found_in_desc],
                detected_objects=found_in_desc,
                needs_clarification=True,
                clarification_question="I found multiple objects. Which one should I create?",
                confidence=0.88
            )

        # 2. Determine target object
        target_canonical = explicit_target or (found_in_desc[0] if len(found_in_desc) == 1 else None)
        
        if not target_canonical:
            if any(k in desc_lower for k in ["chair", "seat", "stool", "armchair"]):
                target_canonical = "chair"
            elif any(k in desc_lower for k in ["table", "desk"]):
                target_canonical = "table"
            elif any(k in desc_lower for k in ["lamp", "light", "lantern"]):
                target_canonical = "lamp"
            elif any(k in desc_lower for k in ["mug", "cup"]):
                target_canonical = "mug"
            elif geom.get("is_lamp"):
                target_canonical = "lamp"
            elif geom.get("is_table"):
                target_canonical = "table"
            elif geom.get("is_mug"):
                target_canonical = "mug"
            else:
                target_canonical = "chair"

        # 3. Object decomposition defaults
        if target_canonical == "chair":
            object_type = "office chair" if ("office" in desc_lower or "gaming" in desc_lower) else "chair"
            components = ["seat", "backrest", "two armrests", "central support", "five-wheel base"]
            features = ["high backrest", "armrests", "five wheels"]
            materials = ["fabric", "plastic", "metal"]
            colors = ["black"]
            styles = ["modern", "ergonomic"]
            synonyms = ["desk chair", "computer chair", "ergonomic chair"]
        elif target_canonical == "table":
            object_type = "dining table"
            components = ["tabletop", "four legs", "support apron"]
            features = ["four legs", "wooden surface"]
            materials = ["natural oak wood"]
            colors = ["natural wood"]
            styles = ["modern", "minimalist"]
            synonyms = ["dining table", "wooden desk", "study table"]
        elif target_canonical == "lamp":
            object_type = "desk lamp"
            components = ["circular base", "slender vertical stem", "conical lampshade", "light bulb"]
            features = ["round base", "adjustable neck", "metal lampshade"]
            materials = ["brushed metal", "frosted glass"]
            colors = ["brass", "white"]
            styles = ["contemporary", "minimalist"]
            synonyms = ["table lamp", "bedside lamp", "desk light"]
        else: # mug
            object_type = "coffee mug"
            components = ["cylindrical body", "ergonomic handle", "base rim"]
            features = ["loop handle", "smooth rim"]
            materials = ["glazed ceramic"]
            colors = ["white"]
            styles = ["minimalist"]
            synonyms = ["tea cup", "ceramic mug", "beverage cup"]

        # 4. Integrate user text modifications
        user_modifications = []
        if "taller" in desc_lower:
            user_modifications.append("increase backrest height slightly" if target_canonical == "chair" else "increase height")
            if "taller backrest" not in features:
                features.append("tall backrest")
        if "leather" in desc_lower:
            materials = ["genuine leather", "metal"]
            user_modifications.append("change material to leather")
        elif "wood" in desc_lower:
            materials = ["natural wood"]
            user_modifications.append("change material to wood")
        elif "metal" in desc_lower:
            materials = ["polished metal"]

        if "blue" in desc_lower:
            colors = ["blue"]
        elif "red" in desc_lower:
            colors = ["red"]
        elif "white" in desc_lower:
            colors = ["white"]

        # 5. Build 5 tiered search queries
        queries = [
            f"{styles[0]} {object_type}",
            object_type,
            f"{object_type} {features[0]}",
            f"{styles[0]} {target_canonical}",
            f"{colors[0]} {object_type}" if colors else synonyms[0]
        ]
        seen = set()
        dedup_queries = []
        for q in queries:
            c = q.strip().lower()
            if c and c not in seen:
                seen.add(c)
                dedup_queries.append(c)

        return GemmaAnalysisResult(
            object_type=object_type,
            canonical_name=target_canonical,
            search_terms=dedup_queries[:5],
            style=styles,
            features=features,
            components=components,
            materials=materials,
            colors=colors,
            user_modifications=user_modifications,
            detected_objects=[object_type],
            needs_clarification=False,
            approximate_scale="human-sized",
            confidence=0.96
        )

gemma_service = GemmaService()

