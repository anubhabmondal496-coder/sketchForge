import os
from fastapi import APIRouter
import torch

from app.config import settings
from app.services.gemma_service import gemma_service
from app.services.tripo_service import tripo_service

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health():
    """
    Returns the operational status of the inference backend,
    GPU availability, VRAM metrics, and model loading state.
    """
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    
    gpu_mem = None
    if cuda_available:
        gpu_mem = {
            "total_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2),
            "allocated_gb": round(torch.cuda.memory_allocated(0) / (1024**3), 2),
            "reserved_gb": round(torch.cuda.memory_reserved(0) / (1024**3), 2),
        }

    return {
        "status": "ok",
        "gpu": cuda_available,
        "device": device_name,
        "models": {
            "gemma": gemma_service.is_available(),
            "tripo": tripo_service.is_available(),
        },
        "mock_mode": settings.MOCK_MODE,
        "gpu_memory": gpu_mem,
    }
