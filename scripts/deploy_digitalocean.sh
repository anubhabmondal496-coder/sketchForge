#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "SketchForge: Deploying to DigitalOcean RTX 4000 Ada"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# 1. Run core GPU environment setup if not already completed
if [ ! -d ".venv" ]; then
    echo "[1/4] Running setup_gpu.sh..."
    bash scripts/setup_gpu.sh
else
    echo "[1/4] Virtual environment exists. Checking packages..."
fi

# 2. Configure Systemd Service
echo "[2/4] Setting up systemd service..."
sudo cp scripts/sketchforge.service /etc/systemd/system/sketchforge.service
sudo systemctl daemon-reload
sudo systemctl enable sketchforge
sudo systemctl restart sketchforge

# 3. Configure Nginx Reverse Proxy
echo "[3/4] Configuring Nginx reverse proxy..."
if [ -f "scripts/nginx_sketchforge.conf" ]; then
    sudo cp scripts/nginx_sketchforge.conf /etc/nginx/sites-available/sketchforge
    sudo ln -sf /etc/nginx/sites-available/sketchforge /etc/nginx/sites-enabled/sketchforge
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
fi

# 4. Check Health Status
echo "[4/4] Verifying backend health..."
sleep 3
curl -s http://127.0.0.1:8000/health | python3 -m json.tool || true

echo "=========================================================="
echo "Deployment Complete!"
echo "Daemon status: sudo systemctl status sketchforge"
echo "Live logs: sudo journalctl -u sketchforge -f"
echo "=========================================================="
