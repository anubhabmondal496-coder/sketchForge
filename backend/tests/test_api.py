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

from PIL import ImageDraw

def create_test_photo_bytes(format="JPEG") -> io.BytesIO:
    img = Image.new("RGB", (256, 256), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Draw chair components with sharp contrast
    draw.rectangle([80, 60, 176, 140], fill=(40, 40, 50))
    draw.rectangle([70, 140, 186, 170], fill=(60, 60, 70))
    draw.rectangle([80, 170, 95, 230], fill=(30, 30, 30))
    draw.rectangle([160, 170, 175, 230], fill=(30, 30, 30))
    for i in range(70, 180, 10):
        draw.line([(i, 60), (i, 140)], fill=(80, 80, 90), width=2)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf

def test_generate_from_photo_flow():
    photo_bytes = create_test_photo_bytes(format="JPEG")
    res = client.post(
        "/api/generate-from-photo",
        files={"image": ("chair.jpg", photo_bytes, "image/jpeg")},
        data={"description": "modern black office chair with armrests"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] in ("processing", "queued", "analyzing")

    # Poll status
    job_id = data["job_id"]
    poll_res = client.get(f"/api/jobs/{job_id}")
    assert poll_res.status_code == 200
    job_data = poll_res.json()
    assert job_data["job_id"] == job_id
    assert job_data["input_type"] == "photo"

def test_generate_from_photo_unsupported_format():
    # Attempt uploading GIF
    img = Image.new("RGB", (100, 100), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    buf.seek(0)

    res = client.post(
        "/api/generate-from-photo",
        files={"image": ("animation.gif", buf, "image/gif")},
        data={"description": "a chair"}
    )
    assert res.status_code == 400
    assert "Unsupported image format" in res.json()["detail"]

def test_generate_from_photo_poor_quality_rejected():
    # Completely flat, blurry/blank image
    flat_img = Image.new("RGB", (256, 256), color=(128, 128, 128))
    buf = io.BytesIO()
    flat_img.save(buf, format="JPEG")
    buf.seek(0)

    res = client.post(
        "/api/generate-from-photo",
        files={"image": ("blank.jpg", buf, "image/jpeg")},
        data={"description": "a chair"}
    )
    assert res.status_code == 400
    assert "difficult to identify" in res.json()["detail"].lower()
