# SketchForge Frontend

Interactive web workbench for SketchForge: 2D drawing canvas to real-time 3D geometry viewer and multimodal refinement loop.

## Architecture & Tech Stack

- **Framework:** React 18 + TypeScript + Vite
- **3D Engine:** Three.js + `@react-three/fiber` + `@react-three/drei`
- **Canvas:** HTML5 Canvas with high-DPI scaling, stroke history, undo/redo, touch prevention
- **Styling:** Engineered slate/charcoal workbench design with cadmium industrial accent

## Local Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173`.

## Environment Variables

Create `.env.local` or set environment variables:

```env
VITE_API_URL=http://localhost:8000
```

## Production Build

```bash
npm run build
```

Build output is written to `frontend/dist/` for static site hosting (e.g., Render Static Site).
