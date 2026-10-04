#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "SketchForge GPU Setup: DigitalOcean NVIDIA RTX 4000 Ada"
echo "=========================================================="

# 1. Update OS packages
echo "[1/11] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3-dev \
    python3-pip \
    python3-venv \
    nginx

# 2. Verify NVIDIA Driver & CUDA
echo "[2/11] Verifying NVIDIA Driver..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. Ensure NVIDIA drivers are installed on the Droplet."
    exit 1
fi
nvidia-smi

echo "[3/11] Checking CUDA Compiler..."
if command -v nvcc &> /dev/null; then
    nvcc --version
else
    echo "Warning: nvcc not in PATH; PyTorch prebuilt CUDA wheels will be utilized."
fi

# 4. Prepare directory layout
echo "[4/11] Preparing workspace directories..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

mkdir -p backend/models
mkdir -p backend/generated

# 5. Create Python Virtual Environment
echo "[5/11] Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# 6. Install PyTorch with CUDA 12.1+ support for Ada Lovelace Architecture
echo "[6/11] Installing PyTorch with CUDA support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 7. Install Transformers and acceleration libraries
echo "[7/11] Installing Transformers, Accelerate, and BitsAndBytes..."
pip install transformers accelerate bitsandbytes sentencepiece

# 8. Install FastAPI and Web Server Stack
echo "[8/11] Installing FastAPI & Uvicorn..."
pip install fastapi uvicorn[standard] pydantic python-multipart httpx requests

# 9. Install TripoSR and Geometry dependencies
echo "[9/11] Installing TripoSR & 3D processing packages..."
pip install trimesh rembg scipy numpy einops omegaconf
if [ ! -d "TripoSR" ]; then
    echo "Cloning TripoSR repository..."
    git clone https://github.com/VAST-AI-Research/TripoSR.git
    pip install -e TripoSR/ || true
fi

# 10. Install backend project dependencies
echo "[10/11] Installing remaining backend requirements..."
pip install -r backend/requirements.txt

# 11. Run Verification Health Check
echo "[11/11] Running validation check..."
python3 -c "
import torch
print('CUDA Available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU Device:', torch.cuda.get_device_name(0))
    print('VRAM Total (GB):', round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2))
"

echo "=========================================================="
echo "GPU Environment Setup Completed Successfully!"
echo "To activate: source .venv/bin/activate"
echo "To start backend: uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000"
echo "=========================================================="
