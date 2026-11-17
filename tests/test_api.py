"""Tests for the HTTP API. They use the real trained model in models/."""

import io

import numpy as np
import pytest
from PIL import Image

from api.server import create_app


@pytest.fixture(scope="module")
def client():
    return create_app().test_client()


def png_bytes(width=256, height=256) -> io.BytesIO:
    pixels = (np.random.default_rng(0).random((height, width, 3)) * 255).astype("uint8")
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok", "model_loaded": True}


def test_meta_lists_classes_and_real_metrics(client):
    meta = client.get("/api/meta").get_json()
    assert len(meta["classes"]) == 38
    assert len(meta["crops"]) == 14
    assert meta["diseases"] == 26
    assert meta["low_confidence_threshold"] == 0.70
    assert 0 < meta["metrics"]["test_accuracy"] <= 1
    assert "history" not in meta["metrics"]


def test_predict_returns_prediction_alternatives_and_advice(client):
    response = client.post("/api/disease/predict", data={"image": (png_bytes(), "leaf.png")},
                           content_type="multipart/form-data")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body["prediction"]) == {"class_name", "crop", "condition", "healthy", "confidence"}
    assert len(body["alternatives"]) == 3
    assert body["alternatives"][0] == body["prediction"]
    assert body["low_confidence"] == (body["prediction"]["confidence"] < 0.70)
    assert body["advice"] is not None and body["disclaimer"]


def test_random_noise_is_flagged_as_low_confidence(client):
    body = client.post("/api/disease/predict", data={"image": (png_bytes(), "noise.png")},
                       content_type="multipart/form-data").get_json()
    assert body["low_confidence"] is True


def test_missing_file(client):
    response = client.post("/api/disease/predict", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "no_file"


def test_file_that_is_not_an_image(client):
    response = client.post("/api/disease/predict",
                           data={"image": (io.BytesIO(b"this is not a photo"), "notes.jpg")},
                           content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_image"


def test_image_that_is_too_small(client):
    response = client.post("/api/disease/predict", data={"image": (png_bytes(16, 16), "tiny.png")},
                           content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "image_too_small"


def test_unknown_api_path_is_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
