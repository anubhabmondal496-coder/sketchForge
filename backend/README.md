# SketchForge Backend

FastAPI multimodal AI inference server powering SketchForge.

## Architectural Responsibilities

- **Multimodal Visual Reasoning Layer:** Gemma 4 E4B (interprets sketch & prompts to output structured `SceneSpec` JSON).
- **3D Reconstruction Engine:** TripoSR (converts preprocessed 2D sketch into watertight 3D mesh).
- **Mesh Export:** Standard binary `.glb` for web rendering and direct download.
- **Asynchronous Task Queue:** In-memory job scheduler with real-time progress polling.

## Local Setup

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

For development without an NVIDIA GPU, enable mock/fallback mode:

```bash
# In .env or shell:
export MOCK_MODE=true
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

- `GET /health` — Check system and GPU readiness.
- `POST /analyze` — Direct Gemma 4 E4B multimodal reasoning from sketch.
- `POST /generate` — Asynchronously queue image-to-3D generation.
- `GET /job/{job_id}` — Poll job status, timings, and stage message.
- `GET /model/{job_id}` — Download or stream the generated GLB file.
- `POST /refine` — Iteratively refine an existing 3D model with new prompt instructions.
