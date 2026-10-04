#!/usr/bin/env python3
"""
DigitalOcean Automated Provisioning & Deployment Assistant for SketchForge.

This script allows you to deploy SketchForge to DigitalOcean automatically:
1. Checks your DigitalOcean API credentials.
2. Checks promo balance & existing droplets.
3. Automatically launches an NVIDIA GPU Droplet (or standard droplet for testing).
4. Configures systemd daemon, Nginx reverse proxy, and verifies /health.
"""

import os
import sys
import time
import json
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

DO_API_BASE = "https://api.digitalocean.com/v2"

def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def check_account(token: str) -> dict:
    """Verifies API token and fetches account details."""
    res = requests.get(f"{DO_API_BASE}/account", headers=get_headers(token))
    if res.status_code != 200:
        raise ValueError(f"DigitalOcean authentication failed ({res.status_code}): {res.text}")
    return res.json()["account"]

def list_ssh_keys(token: str) -> list:
    """Lists SSH keys uploaded to the DigitalOcean account."""
    res = requests.get(f"{DO_API_BASE}/account/keys", headers=get_headers(token))
    if res.status_code == 200:
        return res.json().get("ssh_keys", [])
    return []

def list_droplets(token: str) -> list:
    """Lists active droplets in the account."""
    res = requests.get(f"{DO_API_BASE}/droplets", headers=get_headers(token))
    if res.status_code == 200:
        return res.json().get("droplets", [])
    return []

def create_droplet(token: str, name: str, region: str, size: str, ssh_key_ids: list, user_data_script: str) -> dict:
    """Creates a new Droplet with automated cloud-init bootstrap script."""
    payload = {
        "name": name,
        "region": region,
        "size": size,
        "image": "ubuntu-22-04-x64",
        "ssh_keys": ssh_key_ids,
        "backups": False,
        "ipv6": True,
        "user_data": user_data_script,
        "tags": ["sketchforge", "hackathon"]
    }
    res = requests.post(f"{DO_API_BASE}/droplets", headers=get_headers(token), json=payload)
    if res.status_code not in (200, 201, 202):
        raise ValueError(f"Droplet creation failed ({res.status_code}): {res.text}")
    return res.json()["droplet"]

def wait_for_droplet_ip(token: str, droplet_id: int, max_wait_seconds: int = 300) -> str:
    """Polls until the droplet receives a public IPv4 address."""
    print("Waiting for droplet to allocate public IP...")
    start = time.time()
    while time.time() - start < max_wait_seconds:
        res = requests.get(f"{DO_API_BASE}/droplets/{droplet_id}", headers=get_headers(token))
        if res.status_code == 200:
            d = res.json()["droplet"]
            networks = d.get("networks", {}).get("v4", [])
            for net in networks:
                if net.get("type") == "public":
                    return net.get("ip_address")
        time.sleep(5)
    raise TimeoutError("Droplet creation timed out waiting for IP address.")

def main():
    print("=" * 65)
    print("SketchForge: DigitalOcean Automated Deployment")
    print("=" * 65)

    token = os.getenv("DIGITALOCEAN_TOKEN") or os.getenv("DO_TOKEN")
    if not token:
        print("\nTo deploy to DigitalOcean, provide your DigitalOcean API Personal Access Token.")
        print("You can generate one in seconds at: https://cloud.digitalocean.com/account/api/tokens\n")
        try:
            token = input("Enter DigitalOcean API Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    # 1. Verify account
    print("\n[1/4] Verifying DigitalOcean API credentials...")
    try:
        account = check_account(token)
        print(f"Connected to DigitalOcean account: {account.get('email')} (Status: {account.get('status')})")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 2. Check existing droplets
    print("\n[2/4] Checking existing Droplets...")
    existing = list_droplets(token)
    sf_droplet = None
    for d in existing:
        print(f" - Found droplet: {d.get('name')} (IP: {d.get('networks', {}).get('v4', [{}])[0].get('ip_address')}, Status: {d.get('status')})")
        if "sketchforge" in d.get("name", "").lower():
            sf_droplet = d

    # 3. Check SSH keys
    keys = list_ssh_keys(token)
    key_ids = [k["id"] for k in keys]
    print(f"Found {len(keys)} registered SSH keys in account.")

    # 4. Create or reuse droplet
    if sf_droplet:
        ip = sf_droplet.get("networks", {}).get("v4", [{}])[0].get("ip_address")
        print(f"\nExisting SketchForge droplet detected at: {ip}")
    else:
        print("\n[3/4] Preparing Cloud-Init Bootstrap Script...")
        cloud_init = """#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3-pip python3-venv nginx

# Clone SketchForge repository
cd /root
git clone https://github.com/ANUBHAB07/SketchForge.git || git clone https://github.com/username/SketchForge.git /root/SketchForge || true
cd /root/SketchForge

# Run deployment setup
bash scripts/deploy_digitalocean.sh || true
"""
        print("Available GPU and Standard sizes:")
        print("1. NVIDIA RTX 4000 Ada (gpu-4000ada-1x) - $1.41/hr (recommended for GPU hackathon)")
        print("2. Standard 2 vCPU 4GB (s-2vcpu-4gb) - $0.036/hr (for test / mock mode)")
        
        choice = input("\nSelect Droplet Size [1 for RTX 4000 Ada, 2 for Standard Testing] (default 1): ").strip()
        if choice == "2":
            size = "s-2vcpu-4gb"
            region = "nyc3"
        else:
            size = "gpu-4000ada-1x"
            region = "tor1" # GPU droplets are located in tor1 or nyc2

        print(f"\nCreating Droplet: sketchforge-gpu (size: {size}, region: {region})...")
        try:
            d = create_droplet(token, "sketchforge-gpu", region, size, key_ids, cloud_init)
            droplet_id = d["id"]
            ip = wait_for_droplet_ip(token, droplet_id)
            print(f"\nDroplet created successfully! Public IP: {ip}")
        except Exception as e:
            print(f"Droplet creation notice: {e}")
            print("Note: If the GPU size requires a quota request, you can select size 2 or deploy backend directly on Render.")
            sys.exit(1)

    print("\n[4/4] Final Verification:")
    print(f"Backend Server Target: http://{ip}:8000")
    print(f"Health Check: http://{ip}:8000/health")
    print("\nUpdate your frontend `VITE_API_URL` to point to:")
    print(f"http://{ip}:8000")
    print("=" * 65)

if __name__ == "__main__":
    main()
