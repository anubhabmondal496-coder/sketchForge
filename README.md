# SketchForge

> **From sketch to geometry.** Multimodal 2D-to-3D visual reasoning, legal open-source 3D asset orchestration, and AI-powered geometric reconstruction.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://reactjs.org)
[![Three.js](https://img.shields.io/badge/Three.js-R3F-black.svg)](https://threejs.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

---

## 📖 About SketchForge

**SketchForge** is an intelligent multimodal 3D design and synthesis workstation. It bridges the gap between rough human conceptualization and interactive 3D spatial reality. 

Traditionally, creating 3D assets requires either extensive 3D modeling expertise (Blender, Maya, CAD) or generates redundant AI meshes from scratch when high-quality, open-source 3D models already exist across the web. SketchForge solves this by introducing a **hybrid visual reasoning and asset retrieval pipeline**:

1. **Draw & Express:** A user draws a rough 2D silhouette on an interactive high-DPI canvas and provides an optional natural language description.
2. **Visual Reasoning Layer:** **Google Gemma 4 E4B** acts as a computer vision perception engine—interpreting ambiguous strokes, extracting semantic categories, isolating structural components, bounding scale proportions, and producing normalized search queries.
3. **Asset Search Orchestrator:** Before expending compute on AI mesh generation, SketchForge checks public and legal open-source 3D repositories (e.g., Sketchfab CC/public API, Khronos Sample Assets, SketchForge Architecture Library).
4. **Ranked Auto-Import:** If an asset satisfies legal licensing and passes the strict relevance threshold ($\ge 0.78$), it is downloaded securely and immediately imported into the interactive **Three.js / React Three Fiber** viewport with full attribution metadata.
5. **AI 3D Synthesis Fallback:** If no suitable existing asset is found, the system routes the structured `SceneSpec` directly to **Stability AI TripoSR** and a parametric procedural generator to construct a watertight 3D binary GLB in real-time.

---

## 🏛️ System Architecture

![SketchForge System Architecture](system_architecture.png)

### End-to-End Pipeline

```
USER SKETCH  +  USER PROMPT
            │
            ▼
┌────────────────────────────────────────┐
│  Gemma 4 E4B Multimodal Reasoning     │
│  - Silhouette Computer Vision Analysis │
│  - Normalized Search Queries           │
│  - Structured SceneSpec JSON Schema    │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│      Asset Search Orchestrator         │
│  ├── Sketchfab Provider (CC/Open)      │
│  ├── Open 3D Architecture Registry     │
│  └── Khronos glTF Provider             │
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│          Multi-Factor Ranker           │
│  (Semantic match, category, features,  │
│   license, format quality)             │
└─────────┬────────────────────┬─────────┘
          │                    │
  Score ≥ 0.78         Score < 0.78
 (Asset Found)       (Asset Not Found)
          │                    │
          ▼                    ▼
┌──────────────────┐ ┌───────────────────┐
│ Asset Download   │ │ AI 3D Generation  │
│ Service (Secure  │ │ Fallback Pipeline │
│ HTTPS / GLB)     │ │ (TripoSR / GLB)   │
└─────────┬────────┘ └─────────┬─────────┘
          │                    │
          └──────────┬─────────┘
                     │
                     ▼
┌────────────────────────────────────────┐
│    Interactive Three.js Viewport       │
│  - Dynamic GLTFLoader & Auto-Centering │
│  - Bounding Box Normalization          │
│  - OrbitControls, Wireframe & Shading  │
│  - License & Attribution Attribution   │
└────────────────────────────────────────┘
```

---

## ✨ Key Features

- **Multimodal Visual Reasoning:** Uses Gemma 4 E4B for sketch understanding and prompt normalization without exposing chain-of-thought.
- **Computer Vision Silhouette Detection:** Geometric contour analysis recognizes objects (such as houses, chairs, tables, lamps, and mugs) from freehand sketches.
- **Provider-Agnostic Asset Orchestrator:** Modular search architecture searching legal and open-source 3D providers.
- **Intelligent Multi-Factor Ranking:** Calculates weighted scores based on semantic similarity, object taxonomy, downloadable GLB availability, and license quality.
- **Hardened Download Security:** Validates HTTPS, prevents SSRF/path-traversal, checks MIME types, and verifies GLB magic header bytes (`glTF`).
- **Seamless Three.js Viewport:** Auto-centers, scales, preserves textures, and provides wireframe, camera reset, and mesh export controls.
- **Attribution & Transparency:** Displays author, source URL, and license badges for imported models.
- **Robust AI Fallback:** Integrates TripoSR and parametric procedural reconstruction so users always receive a complete 3D model.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Three.js, `@react-three/fiber`, `@react-three/drei` |
| **Backend** | FastAPI, Uvicorn, Python 3.10+, Pydantic v2 |
| **AI & Vision** | Google Gemma 4 E4B, Stability AI TripoSR, Trimesh, NumPy, SciPy |
| **3D Formats** | GLTF / Binary GLB (`model/gltf-binary`) |
| **Search & Providers**| Provider-Agnostic Asset Search Engine, Mock Open Provider, Sketchfab Open API |
| **Deployment** | Docker, Docker Compose, Nginx, Vercel / Render ready |

---

## 🚀 Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

pip install -r requirements.txt

# Run in development mode (CPU/Mock mode)
uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000` (`http://localhost:8000/docs` for Swagger UI).

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

## 🔍 CLI 3D Search & Interactive Viewer

SketchForge includes a standalone Python tool to search open 3D repositories, download models, and view them immediately:

```bash
python scripts/search_and_view_3d.py --query "cottage house with pitched roof"
```
Or search for furniture:
```bash
python scripts/search_and_view_3d.py --query "modern office chair"
```

---

## 🚢 Deployment Guide

### Option A: Docker Compose (GPU Server / Cloud VM)

For deployment on an NVIDIA GPU instance (RunPod, Lambda Labs, AWS EC2 G5, GCP):

```bash
# 1. Configure environment
cp .env.example .env

# 2. Build and launch backend + frontend containers
docker compose up -d --build

# 3. Check status
docker compose ps
curl http://localhost:8000/health
```

### Option B: Split Cloud Deployment (Vercel + Render)

- **Frontend (Vercel):**
  - Root Directory: `frontend`
  - Build Command: `npm run build`
  - Output Directory: `dist`
  - Environment Variable: `VITE_API_URL=https://your-backend.onrender.com`

- **Backend (Render / Railway):**
  - Root Directory: `backend`
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Environment Variables: `MOCK_MODE=true`, `FRONTEND_URL=https://your-frontend.vercel.app`

### Option C: Instant Public Tunnel for Demos

To share your running local demo with judges:
```bash
# Expose frontend (port 5173)
npx --yes localtunnel --port 5173

# Expose backend (port 8000)
npx --yes localtunnel --port 8000
```

---

## 🧪 Testing

### Backend Unit & Integration Tests
```bash
cd backend
python -m pytest tests/test_asset_pipeline.py
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## 📄 License

Licensed under the [Apache 2.0 License](LICENSE).
