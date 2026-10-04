# SketchForge

> **From sketch to geometry.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://reactjs.org)
[![Three.js](https://img.shields.io/badge/Three.js-R3F-black.svg)](https://threejs.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

SketchForge is a full-stack, AI-powered engineering prototype that converts rough 2D hand-drawn object sketches into interactive 3D geometry in real-time. Designed specifically as a lean, cost-efficient, production-grade hackathon system, it leverages **Google Gemma 4 E4B** for multimodal visual reasoning and planning, **Stability AI TripoSR** for fast image-to-3D mesh reconstruction, and **React Three Fiber (Three.js)** for client-side 3D inspection and iterative refinement.

---

## 1. What It Does

SketchForge provides a streamlined three-stage creative engineering loop:

1. **Draw:** Users draw a rough 2D silhouette on an interactive high-DPI canvas (mouse, trackpad, or touch) and optionally describe the object in natural language (e.g., *"A wooden chair with four legs and a slatted backrest"*).
2. **Understand:** Gemma 4 E4B evaluates the sketch and text, identifies object taxonomy, decomposes constituent parts, bounds 3D proportions, and emits a strictly validated Pydantic **SceneSpec JSON**.
3. **Generate & Refine:** TripoSR synthesizes the preprocessed sketch into a watertight 3D mesh exported as standard binary GLB. The client loads the GLB into an interactive Three.js viewport where users can rotate, pan, zoom, inspect wireframes, download the file, or enter natural-language refinement instructions (e.g., *"Make the backrest taller and add armrests"*) to trigger iterative re-generation.

---

## 2. Demo Workflow (60–90 Seconds)

```text
[Step 1: Draw]     User draws a chair silhouette and types "A simple wooden chair"
         ↓
[Step 2: Reason]   Gemma 4 E4B parses visual features → Emits SceneSpec v1 JSON
         ↓
[Step 3: Generate] TripoSR reconstructs 3D mesh → Exports model.glb (~10-15s)
         ↓
[Step 4: Inspect]  Three.js renders model: OrbitControls, Wireframe toggle, Grid
         ↓
[Step 5: Refine]   User enters "Make the backrest taller and add armrests"
         ↓
[Step 6: Update]   Gemma updates SceneSpec to v2 → TripoSR updates model
         ↓
[Step 7: Export]   User clicks "Download GLB" to save the 3D model
```

---

## 3. Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client (Render Static Site)"]
        UI["SketchForge UI (React + TypeScript)"]
        Canvas["HTML5 Sketch Canvas (High-DPI)"]
        Viewer["Three.js GLB Viewer (@react-three/fiber)"]
        RefineUI["Refinement & Version History Panel"]
    end

    subgraph Backend["AI Inference Server (DigitalOcean RTX 4000 Ada Droplet)"]
        API["FastAPI Backend (Uvicorn / Nginx HTTPS)"]
        Jobs["In-Memory Async Job Queue & Telemetry"]
        Prep["Image Preprocessing & Normalization"]
        
        subgraph ReasoningLayer["Reasoning & Planning Layer"]
            Gemma["Google Gemma 4 E4B (4-bit Quantized)"]
            SpecValidator["Pydantic SceneSpec Validator"]
        end

        subgraph GeometryLayer["3D Geometry Layer"]
            Tripo["Stability AI TripoSR"]
            MeshExporter["GLB Mesh Exporter (Trimesh)"]
        end
    end

    Canvas -->|Raw Sketch PNG + Prompt| UI
    UI -->|POST /generate| API
    API --> Jobs
    Jobs --> Prep
    Prep --> Gemma
    Gemma --> SpecValidator
    SpecValidator -->|Validated SceneSpec JSON| Tripo
    Tripo --> MeshExporter
    MeshExporter -->|model.glb| API
    API -->|GET /job/{id} polling| UI
    API -->|GET /model/{id} binary stream| Viewer
    RefineUI -->|POST /refine + SceneSpec v1| API
```

---

## 4. Technology Stack

### Frontend
- **Framework:** React 18, TypeScript, Vite
- **3D Graphics:** Three.js, `@react-three/fiber`, `@react-three/drei`
- **Canvas:** Native HTML5 2D Canvas with sub-pixel DPR scaling, touch lock, and stroke history
- **Design System:** Engineered slate/charcoal workbench theme with cadmium industrial accent (`#ea580c`), system platform typography

### Backend & AI Inference
- **API Framework:** FastAPI, Uvicorn, Pydantic v2
- **Image Processing:** Pillow, NumPy, SciPy, Rembg
- **Multimodal AI:** Google Gemma 4 E4B (`transformers`, `bitsandbytes` 4-bit NF4)
- **3D Reconstruction Engine:** Stability AI TripoSR, Trimesh
- **Task Scheduling:** Asynchronous job manager with status polling and telemetry logging

---

## 5. Gemma's Role vs. TripoSR's Role

> [!IMPORTANT]
> **Clear Responsibility Separation:**
> - **Gemma 4 E4B is NOT the 3D mesh generator.** Gemma acts strictly as the **multimodal reasoning and planning layer**. It interprets ambiguous 2D strokes, extracts semantic context from natural language prompts, predicts structural components, bounds geometry proportions, and generates a strict structured `SceneSpec`.
> - **TripoSR is the 3D reconstruction engine.** It processes normalized silhouettes and reconstructs dense, watertight 3D geometries exported to `.glb`.
> - **Three.js** is the client rendering layer for inspection, camera orbit, and wireframe analysis.

---

## 6. SceneSpec JSON Schema

Gemma 4 E4B outputs a strictly validated schema:

```json
{
  "object": "chair",
  "confidence": 0.92,
  "style": "simple wooden craftsmanship",
  "material": "scandinavian beech wood",
  "components": [
    "seat cushion",
    "slatted backrest",
    "four tapered legs",
    "leg stretchers"
  ],
  "geometry": {
    "width": 0.5,
    "depth": 0.48,
    "height": 0.92,
    "back_height": 0.85
  },
  "generation_prompt": "A handcrafted wooden chair with four tapered legs and a tall slatted backrest."
}
```

---

## 7. Local Development

### Prerequisites
- Node.js 18+ (tested on Node v24)
- Python 3.10+
- (Optional) NVIDIA GPU with CUDA 12.1+; or use built-in `MOCK_MODE=true` for CPU development.

### Setup Backend

```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

pip install -r requirements.txt

# For local development without a GPU:
export MOCK_MODE=true    # Linux / macOS
# set MOCK_MODE=true     # Windows CMD
# $env:MOCK_MODE="true"  # Windows PowerShell

uvicorn app.main:app --reload --port 8000
```

### Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173` and connect to `http://localhost:8000`.

---

## 8. GPU Setup (DigitalOcean RTX 4000 Ada)

For production deployment on a DigitalOcean GPU droplet:

```bash
chmod +x scripts/setup_gpu.sh scripts/download_models.sh
./scripts/setup_gpu.sh
```

The setup script handles:
1. OS dependencies (`build-essential`, `ffmpeg`, `libgl1-mesa-glx`)
2. Driver and CUDA validation
3. PyTorch CUDA 12.1 installation
4. Transformers, BitsAndBytes, and TripoSR dependencies
5. Model cache configuration and directory verification

---

## 9. Environment Variables

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `HF_TOKEN` | *(empty)* | Hugging Face token required on backend for Gemma weights access |
| `MODEL_CACHE_DIR` | `./models` | Persistent directory for cached model weights |
| `DEVICE` | `cuda` | Target compute device (`cuda` or `cpu`) |
| `MOCK_MODE` | `false` | Enable deterministic development mode without GPU |
| `GEMMA_MODEL_ID` | `google/gemma-4-E4B-it` | Official Hugging Face repository ID |
| `LOAD_IN_4BIT` | `true` | Enable 4-bit BitsAndBytes quantization to minimize VRAM |
| `TRIPOSR_MODEL_ID` | `stabilityai/TripoSR` | Official TripoSR repository checkpoint |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin (set to Render domain in prod) |
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL |
| `VITE_API_URL` | `http://localhost:8000` | Client API endpoint (injected during Vite build) |

---

## 10. DigitalOcean Deployment (GPU Droplet)

> [!TIP]
> **Credit Budgeting ($25 GPU Credit):** Only spin up the RTX 4000 Ada Droplet during active development, testing, and the live hackathon demonstration. Shut down or snapshot the droplet when idle.

1. **Create Droplet:**
   - Image: Ubuntu 22.04 LTS with NVIDIA GPU drivers
   - Size: GPU Droplet (1x NVIDIA RTX 4000 Ada 20GB VRAM)
2. **SSH into Droplet:**
   ```bash
   ssh root@<DROPLET_IP>
   ```
3. **Clone and Configure:**
   ```bash
   git clone https://github.com/<your-user>/SketchForge.git
   cd SketchForge
   cp .env.example .env
   nano .env  # Add HF_TOKEN and FRONTEND_URL
   ```
4. **Run GPU Setup:**
   ```bash
   bash scripts/setup_gpu.sh
   bash scripts/download_models.sh
   ```
5. **Configure systemd Service:**
   ```ini
   # /etc/systemd/system/sketchforge.service
   [Unit]
   Description=SketchForge FastAPI Daemon
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/SketchForge/backend
   EnvironmentFile=/root/SketchForge/.env
   ExecStart=/root/SketchForge/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now sketchforge
   ```
6. **Configure Nginx Reverse Proxy with SSL (Certbot):**
   ```nginx
   server {
       server_name api.yourdomain.com;
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

---

## 11. Render Deployment (Frontend Static Site)

The frontend is independently hosted as a Render Static Site:

1. Create a **New Static Site** on Render linked to this repository.
2. Settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
3. Environment Variables:
   - `VITE_API_URL`: `https://api.yourdomain.com` (or your DigitalOcean Droplet HTTPS address)
4. Deploy site.

---

## 12. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check GPU status, device name, VRAM memory metrics, and model status |
| `POST` | `/analyze` | Direct Gemma 4 E4B multimodal reasoning; returns `SceneSpec` JSON |
| `POST` | `/generate` | Multipart upload (sketch image + description); returns `{ job_id, status }` |
| `GET` | `/job/{job_id}` | Poll generation status (`queued`, `analyzing`, `generating`, `completed`, `failed`) |
| `GET` | `/model/{job_id}` | Download or stream the reconstructed binary `.glb` model |
| `POST` | `/refine` | Submit prior `SceneSpec` + prompt update to generate a refined 3D version |

---

## 13. Project Limitations

- **Single 2D Viewpoint:** A single silhouette sketch does not contain backside or internal geometry; TripoSR infers occluded views generatively.
- **Organic Complexity:** Reconstructions work best on clear, recognizable silhouettes (furniture, homeware, vehicles). Highly organic or chaotic shapes may contain visual artifacts.
- **Non-CAD Geometry:** Output meshes are generative polygonal representations, not dimensionally certified manufacturing CAD models.

---

## 14. Demo Presets

The canvas toolbar contains one-click test presets optimized for 3D reconstruction:
- **Chair** — Handcrafted chair with seat, backrest, and four legs
- **Table** — Four-legged dining table
- **Lamp** — Weighted base studio bedside lamp
- **Mug** — Ceramic coffee cup with ergonomic handle

---

## 15. Testing

### Run Backend Unit & Integration Tests
```bash
cd backend
python -m pytest
```

### Run Pipeline Integration Test
```bash
python scripts/test_pipeline.py
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

---

## 16. License

Apache 2.0 License. See [LICENSE](LICENSE) for details.
