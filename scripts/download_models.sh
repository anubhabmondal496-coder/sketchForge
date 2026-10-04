#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "SketchForge Model Cache Pre-downloader"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

CACHE_DIR="${MODEL_CACHE_DIR:-$ROOT_DIR/backend/models}"
mkdir -p "$CACHE_DIR"

echo "Model Cache Directory: $CACHE_DIR"

# 1. Download / Cache TripoSR weights
echo "[1/2] Checking TripoSR model weights..."
python3 -c "
import os
from huggingface_hub import snapshot_download
model_id = 'stabilityai/TripoSR'
cache_dir = '$CACHE_DIR'
print(f'Caching {model_id}...')
snapshot_download(repo_id=model_id, local_dir=os.path.join(cache_dir, 'triposr'), token=os.getenv('HF_TOKEN'))
print('TripoSR model cached successfully.')
"

# 2. Download / Cache Gemma 4 E4B weights
echo "[2/2] Checking Gemma 4 E4B weights..."
python3 -c "
import os
from huggingface_hub import snapshot_download
model_id = os.getenv('GEMMA_MODEL_ID', 'google/gemma-4-E4B-it')
cache_dir = '$CACHE_DIR'
token = os.getenv('HF_TOKEN')
if not token:
    print('WARNING: HF_TOKEN is not set. Gemma weights require Hugging Face gated access token.')
    print('Set HF_TOKEN in your .env file to enable pre-download.')
else:
    print(f'Caching {model_id}...')
    snapshot_download(repo_id=model_id, local_dir=os.path.join(cache_dir, 'gemma-4-e4b'), token=token)
    print('Gemma 4 E4B model cached successfully.')
"

echo "=========================================================="
echo "Model caching routine finished."
echo "=========================================================="
