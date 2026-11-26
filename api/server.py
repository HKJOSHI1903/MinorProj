"""Kisan Sahayak backend: a small Flask API around the trained model.

    python -m api.server            # http://localhost:8000

Endpoints
    GET  /api/health            is the server up, is the model loaded
    GET  /api/meta              classes, crops, real training metrics, threshold
    POST /api/disease/predict   form field "image" -> disease, confidence, advice
    GET  /api/crop/meta         crops, input ranges and presets, real model metrics
    POST /api/crop/recommend    JSON with N, P, K, temperature, humidity, ph, rainfall
    GET  /api/chat/status       whether an API key is set, how many documents are indexed
    POST /api/chat              JSON with message, language, history, context

When the Vue app has been built (web/dist exists) this server also serves it,
so the whole product runs from this one command.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException

from kisan.chatbot import chat, retriever
from kisan.crop import predict as crop
from kisan.disease.labels import advice_disclaimer, parse_label, treatment_advice
from kisan.disease.predict import LOW_CONFIDENCE, ModelNotTrained, load_model, predict
from kisan.disease.quality import assess as assess_quality

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / "web" / "dist"
METRICS_PATH = ROOT / "reports" / "metrics.json"
CROP_METRICS_PATH = ROOT / "reports" / "crop" / "metrics.json"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_SIDE = 32                        # photos smaller than this cannot be judged


class ApiError(Exception):
    """An error the web app shows to the user. `code` picks the translated message."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def label_json(label, confidence: float | None = None) -> dict:
    data = {"class_name": label.class_name, "crop": label.crop,
            "condition": label.condition, "healthy": label.healthy}
    if confidence is not None:
        data["confidence"] = round(confidence, 4)
    return data


def read_photo(file) -> Image.Image:
    """Open the uploaded file, or raise an ApiError explaining what is wrong with it."""
    try:
        image = Image.open(file.stream)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ApiError(400, "invalid_image", "This file is not a photo. Use a JPG or PNG image.")
    if min(image.size) < MIN_SIDE:
        raise ApiError(400, "image_too_small", "This photo is too small. Take a closer, clearer photo.")
    return image


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return jsonify(error={"code": error.code, "message": error.message}), error.status

    @app.errorhandler(ModelNotTrained)
    def model_missing(_error):
        return jsonify(error={"code": "model_missing",
                              "message": "The model has not been trained yet."}), 503

    @app.errorhandler(crop.CropModelNotTrained)
    def crop_model_missing(_error):
        return jsonify(error={"code": "model_missing",
                              "message": "The crop model has not been trained yet."}), 503

    @app.errorhandler(crop.InvalidInput)
    def invalid_input(error: crop.InvalidInput):
        return jsonify(error={"code": "invalid_input", "field": error.field, "message": str(error)}), 400

    @app.errorhandler(retriever.IndexNotBuilt)
    def index_missing(_error):
        return jsonify(error={"code": "index_missing",
                              "message": "The knowledge base has not been indexed yet."}), 503

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        code = "file_too_large" if error.code == 413 else "http_error"
        return jsonify(error={"code": code, "message": error.description}), error.code

    @app.get("/api/health")
    def health():
        try:
            load_model()
            return jsonify(status="ok", model_loaded=True)
        except ModelNotTrained:
            return jsonify(status="ok", model_loaded=False)

    @app.get("/api/meta")
    def meta():
        _, class_names, image_size, _temperature = load_model()
        labels = [parse_label(name) for name in class_names]
        metrics = None
        if METRICS_PATH.exists():
            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            metrics.pop("history", None)  # per-epoch numbers are not needed by the web app
        return jsonify(
            classes=[label_json(label) for label in labels],
            crops=sorted({label.crop for label in labels}),
            diseases=sum(not label.healthy for label in labels),
            image_size=image_size,
            low_confidence_threshold=LOW_CONFIDENCE,
            metrics=metrics,
            disclaimer=advice_disclaimer(),
        )

    @app.post("/api/disease/predict")
    def disease_predict():
        file = request.files.get("image")
        if file is None or not file.filename:
            raise ApiError(400, "no_file", "No photo was sent.")
        image = read_photo(file)

        # Too dark, blurred, grainy, too small...: the app shows how to retake the photo.
        photo_quality = assess_quality(image)
        results = predict(image, top_k=3, issues=photo_quality.issues)
        best = results[0]
        return jsonify(
            prediction=label_json(best.label, best.confidence),
            # Below 70% the web app tells the farmer not to rely on the result
            # and to consult the local KVK or agriculture officer.
            low_confidence=best.confidence < LOW_CONFIDENCE,
            threshold=LOW_CONFIDENCE,
            quality=photo_quality.to_json(),
            alternatives=[label_json(r.label, r.confidence) for r in results],
            advice=treatment_advice(best.label.class_name),
            disclaimer=advice_disclaimer(),
        )

    # ---- Module 2: crop recommendation ----
    @app.get("/api/crop/meta")
    def crop_meta():
        bundle, profiles = crop.load()
        metrics = None
        if CROP_METRICS_PATH.exists():
            metrics = json.loads(CROP_METRICS_PATH.read_text(encoding="utf-8"))
        return jsonify(crops=bundle["classes"], features=profiles["features"], limits=crop.LIMITS,
                       model=bundle["name"], metrics=metrics, low_confidence_threshold=crop.LOW_CONFIDENCE)

    @app.post("/api/crop/recommend")
    def crop_recommend():
        values = request.get_json(silent=True)
        if not isinstance(values, dict):
            raise ApiError(400, "invalid_input", "Send the seven values as JSON.")
        return jsonify(crop.recommend(values))

    # ---- Module 3: the farming assistant ----
    @app.get("/api/chat/status")
    def chat_status():
        return jsonify(ai_available=chat.ai_available(), documents=retriever.document_count(),
                       helpline=chat.HELPLINE)

    @app.post("/api/chat")
    def chat_message():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ApiError(400, "invalid_input", "Send the message as JSON.")
        message = body.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ApiError(400, "empty_message", "Type a question first.")
        history = body.get("history") if isinstance(body.get("history"), list) else []
        context = body.get("context") if isinstance(body.get("context"), dict) else None
        language = "hi" if body.get("language") == "hi" else "en"
        return jsonify(chat.answer(message, language=language, context=context,
                                   history=[turn for turn in history if isinstance(turn, dict)]))

    # ---- The built Vue app (only present after `npm run build` in web/) ----
    @app.get("/")
    @app.get("/<path:path>")
    def web(path: str = ""):
        if path.startswith("api/"):
            raise ApiError(404, "not_found", "Unknown API endpoint.")
        if not WEB_DIST.exists():
            return ("The web app has not been built yet. Run `npm install` and `npm run build` "
                    "in the web/ folder, or use `npm run dev` while developing."), 503
        if path and (WEB_DIST / path).is_file():
            return send_from_directory(WEB_DIST, path)
        return send_from_directory(WEB_DIST, "index.html")  # Vue Router handles the URL

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the Kisan Sahayak server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app()
    try:
        print("Loading the model...")
        load_model()
    except ModelNotTrained as error:
        print(f"Warning: {error}")
    print(f"Kisan Sahayak is running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
