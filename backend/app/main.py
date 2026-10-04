import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import health, analyze, generate, refine

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("sketchforge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup banner
    logger.info("=" * 60)
    logger.info("Starting SketchForge Backend Engine")
    logger.info(f"Device: {settings.DEVICE}")
    logger.info(f"Mock Mode: {settings.MOCK_MODE}")
    logger.info(f"CORS Allowed Origins: {settings.cors_origins}")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down SketchForge Backend Engine")

app = FastAPI(
    title="SketchForge API",
    description="Multimodal 2D-to-3D Geometry Reconstruction Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS strictly according to deployment rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Logging middleware for performance telemetry
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if not request.url.path.startswith("/health"):
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred during 3D processing. Please retry."}
    )

# Include Routers
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(generate.router)
app.include_router(refine.router)

@app.get("/")
def root():
    return {
        "app": "SketchForge",
        "tagline": "From sketch to geometry",
        "status": "online",
        "docs": "/docs"
    }
