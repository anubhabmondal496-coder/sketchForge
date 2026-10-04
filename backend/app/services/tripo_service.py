import os
import gc
import time
import logging
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np

import torch
import trimesh

from app.config import settings
from app.models.scene_spec import SceneSpec

logger = logging.getLogger("sketchforge.tripo")

class TripoService:
    def __init__(self):
        self._model = None
        self._loaded = False
        self._device = None

    def is_available(self) -> bool:
        if settings.MOCK_MODE:
            return True
        return torch.cuda.is_available()

    def get_model(self):
        """
        Lazy-loads TripoSR model using official TSR architecture.
        Keeps model resident during active GPU server operation.
        """
        if self._loaded and self._model is not None:
            return self._model

        if settings.MOCK_MODE:
            logger.info("TripoService: Running in MOCK_MODE, using procedural geometry engine.")
            self._loaded = True
            return None

        if not torch.cuda.is_available():
            logger.warning("CUDA is not available. Real TripoSR requires NVIDIA GPU for real-time 3D reconstruction.")
            return None

        start_time = time.time()
        self._device = "cuda:0"
        logger.info(f"Loading TripoSR weights from {settings.TRIPOSR_MODEL_ID} onto {self._device}...")

        try:
            # TripoSR import
            from tsr.system import TSR

            model = TSR.from_pretrained(
                settings.TRIPOSR_MODEL_ID,
                config_name="config.yaml",
                weight_name="model.ckpt"
            )
            model.renderer.set_chunk_size(settings.TRIPOSR_CHUNK_SIZE)
            model.to(self._device)
            self._model = model
            self._loaded = True

            load_duration = time.time() - start_time
            logger.info(f"TripoSR model loaded into GPU memory in {load_duration:.2f}s")
            return self._model
        except Exception as e:
            logger.exception(f"Failed to load TripoSR model: {e}")
            return None

    def unload_model(self):
        """Explicitly frees VRAM when GPU server needs to deallocate resources."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("TripoSR model unloaded and VRAM cleared.")

    def reconstruct(
        self,
        image_path: Path,
        output_glb_path: Path,
        scene_spec: Optional[SceneSpec] = None
    ) -> Path:
        """
        Executes image-to-3D reconstruction and exports the output as GLB.
        """
        start_time = time.time()
        output_glb_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if real GPU TripoSR is possible
        model = self.get_model()

        if model is not None and torch.cuda.is_available():
            logger.info(f"Executing real TripoSR 3D reconstruction on {image_path}...")
            try:
                # 1. Background removal using rembg if needed
                from rembg import remove
                with Image.open(image_path) as raw_img:
                    bg_removed = remove(raw_img.convert("RGBA"))
                
                # Composite onto white or standard background for TSR input
                rgba = np.array(bg_removed).astype(np.float32) / 255.0
                rgb = rgba[..., :3] * rgba[..., 3:4] + (1.0 - rgba[..., 3:4]) * 1.0
                input_image = Image.fromarray((rgb * 255).astype(np.uint8))

                # 2. Run TripoSR forward pass
                with torch.no_grad():
                    scene_codes = model([input_image], device=self._device)
                
                # 3. Extract mesh via Marching Cubes
                meshes = model.extract_mesh(
                    scene_codes,
                    resolution=settings.TRIPOSR_MC_RESOLUTION,
                    has_vertex_color=True
                )
                
                mesh = meshes[0]

                # 4. Export as GLB
                # trimesh handles glb export directly
                mesh.export(str(output_glb_path), file_type="glb")

                duration = time.time() - start_time
                file_size_kb = output_glb_path.stat().st_size / 1024
                logger.info(
                    f"TripoSR reconstruction finished in {duration:.2f}s. GLB size: {file_size_kb:.1f} KB"
                )

                # Memory hygiene
                torch.cuda.empty_cache()
                return output_glb_path

            except Exception as e:
                logger.exception(f"Real TripoSR generation failed: {e}. Falling back to procedural geometry.")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        # Fallback / Mock Mode: Procedural GLB Mesh Generator
        logger.info("Generating procedural GLB geometry for scene specification...")
        self._generate_procedural_glb(output_glb_path, scene_spec)
        duration = time.time() - start_time
        logger.info(f"Procedural 3D model generated in {duration:.2f}s -> {output_glb_path}")
        return output_glb_path

    def _generate_procedural_glb(self, output_path: Path, scene_spec: Optional[SceneSpec]):
        """
        Creates a real, watertight parametric 3D GLB mesh based on the SceneSpec.
        Used for local development without GPU and mock fallback.
        """
        obj_name = (scene_spec.object if scene_spec else "chair").lower()
        geo = scene_spec.geometry if scene_spec else None

        # Material colors (warm oak, brushed metal, modern ceramic)
        mat_color = [180, 110, 50, 255] # default warm wood
        if scene_spec and scene_spec.material:
            m_lower = scene_spec.material.lower()
            if "metal" in m_lower or "steel" in m_lower or "aluminum" in m_lower:
                mat_color = [170, 175, 185, 255]
            elif "ceramic" in m_lower or "porcelain" in m_lower:
                mat_color = [240, 235, 225, 255]
            elif "glass" in m_lower:
                mat_color = [200, 220, 240, 200]

        parts = []

        if "table" in obj_name:
            w = geo.width if (geo and geo.width) else 1.2
            d = geo.depth if (geo and geo.depth) else 0.8
            h = geo.height if (geo and geo.height) else 0.75
            
            # Table top
            top = trimesh.creation.box(extents=[w, d, 0.05])
            top.apply_translation([0, 0, h - 0.025])
            parts.append(top)

            # 4 Legs
            leg_r = 0.025
            leg_h = h - 0.05
            for lx in [-w/2 + 0.08, w/2 - 0.08]:
                for ly in [-d/2 + 0.08, d/2 - 0.08]:
                    leg = trimesh.creation.cylinder(radius=leg_r, height=leg_h)
                    leg.apply_translation([lx, ly, leg_h/2])
                    parts.append(leg)

        elif "lamp" in obj_name:
            h = geo.height if (geo and geo.height) else 0.6
            # Base
            base = trimesh.creation.cylinder(radius=0.12, height=0.03)
            base.apply_translation([0, 0, 0.015])
            parts.append(base)
            # Stem
            stem = trimesh.creation.cylinder(radius=0.015, height=h - 0.2)
            stem.apply_translation([0, 0, (h - 0.2)/2 + 0.03])
            parts.append(stem)
            # Shade
            shade = trimesh.creation.cone(radius=0.18, height=0.18)
            shade.apply_translation([0, 0, h - 0.09])
            parts.append(shade)

        elif "mug" in obj_name or "cup" in obj_name:
            # Cup body
            cup = trimesh.creation.cylinder(radius=0.08, height=0.14)
            cup.apply_translation([0, 0, 0.07])
            parts.append(cup)
            # Handle torus
            handle = trimesh.creation.torus(major_radius=0.05, minor_radius=0.012)
            # Rotate handle to side
            rot = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
            handle.apply_transform(rot)
            handle.apply_translation([0.1, 0, 0.07])
            parts.append(handle)

        else:
            # Default: Parametric Chair with seat, backrest, legs, and optional armrests
            w = geo.width if (geo and geo.width) else 0.5
            d = geo.depth if (geo and geo.depth) else 0.48
            total_h = geo.height if (geo and geo.height) else 0.92
            seat_h = 0.45
            back_h = total_h - seat_h

            # Seat
            seat = trimesh.creation.box(extents=[w, d, 0.04])
            seat.apply_translation([0, 0, seat_h])
            parts.append(seat)

            # 4 Legs
            for lx in [-w/2 + 0.04, w/2 - 0.04]:
                for ly in [-d/2 + 0.04, d/2 - 0.04]:
                    leg = trimesh.creation.cylinder(radius=0.02, height=seat_h)
                    leg.apply_translation([lx, ly, seat_h / 2])
                    parts.append(leg)

            # Backrest posts
            post_h = back_h
            for bx in [-w/2 + 0.04, w/2 - 0.04]:
                post = trimesh.creation.cylinder(radius=0.018, height=post_h)
                post.apply_translation([bx, -d/2 + 0.04, seat_h + post_h / 2])
                parts.append(post)

            # Backrest top slab
            slab = trimesh.creation.box(extents=[w - 0.04, 0.03, 0.14])
            slab.apply_translation([0, -d/2 + 0.04, seat_h + post_h - 0.08])
            parts.append(slab)

            # Optional armrests if specified in SceneSpec components
            has_armrests = scene_spec and scene_spec.components and any(
                "armrest" in c.lower() for c in scene_spec.components
            )
            if has_armrests:
                arm_h = 0.22
                for ax in [-w/2 + 0.02, w/2 - 0.02]:
                    # Vertical support
                    supp = trimesh.creation.cylinder(radius=0.014, height=arm_h)
                    supp.apply_translation([ax, d/4, seat_h + arm_h/2])
                    parts.append(supp)
                    # Horizontal rest
                    rest = trimesh.creation.box(extents=[0.04, d * 0.7, 0.02])
                    rest.apply_translation([ax, 0, seat_h + arm_h])
                    parts.append(rest)

        # Concatenate into watertight mesh
        combined = trimesh.util.concatenate(parts)
        combined.visual.vertex_colors = np.array([mat_color for _ in range(len(combined.vertices))], dtype=np.uint8)

        # Export as GLB
        combined.export(str(output_path), file_type="glb")

tripo_service = TripoService()
