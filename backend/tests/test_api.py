import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.config import settings

client = TestClient(app)

def create_test_image_bytes() -> io.BytesIO:
    img = Image.new("RGB", (256, 256), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "gpu" in data
    assert "models" in data

def test_analyze_endpoint():
    img_bytes = create_test_image_bytes()
    response = client.post(
        "/analyze",
        files={"image": ("test.png", img_bytes, "image/png")},
        data={"description": "a simple wooden chair"}
    )
    assert response.status_code == 200
    spec = response.json()
    assert "object" in spec
    assert "confidence" in spec

def test_generate_and_poll_flow():
    img_bytes = create_test_image_bytes()
    # 1. Post generation job
    gen_res = client.post(
        "/generate",
        files={"image": ("test.png", img_bytes, "image/png")},
        data={"description": "wooden dining table"}
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "job_id" in gen_data
    job_id = gen_data["job_id"]

    # 2. Poll job status
    poll_res = client.get(f"/job/{job_id}")
    assert poll_res.status_code == 200
    job_data = poll_res.json()
    assert job_data["job_id"] == job_id
    assert "status" in job_data

def test_invalid_image_upload():
    response = client.post(
        "/generate",
        files={"image": ("corrupted.txt", io.BytesIO(b"not an image"), "text/plain")},
        data={"description": "test"}
    )
    assert response.status_code == 400
