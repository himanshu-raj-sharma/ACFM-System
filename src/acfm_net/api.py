"""Flask API for real-time ACFM frame analysis."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from .service import MonitoringService


def create_app(model_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 7 * 1024 * 1024
    allowed_origin = os.environ.get("ACFM_ALLOWED_ORIGIN", "http://127.0.0.1:3000")
    allowed_origins = {
        origin.strip() for origin in allowed_origin.split(",") if origin.strip()
    }
    configured_path = model_path or os.environ.get("ACFM_MODEL_PATH")
    if not configured_path:
        raise RuntimeError(
            "ACFM_MODEL_PATH is required. Train a labelled model before starting.",
        )
    service = MonitoringService(configured_path)

    @app.get("/api/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok", "service": "acfm-net"}), 200

    @app.after_request
    def add_security_headers(response):
        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/api/analyze", methods=["OPTIONS"])
    def analyze_options():
        if request.headers.get("Origin") not in allowed_origins:
            return jsonify({"error": "origin is not allowed"}), 403
        return "", 204

    @app.post("/api/analyze")
    def analyze() -> tuple[object, int]:
        if request.headers.get("Origin") not in allowed_origins:
            return jsonify({"error": "origin is not allowed"}), 403
        body = request.get_json(silent=True) or {}
        if body.get("consent") is not True:
            return jsonify({"error": "explicit camera consent is required"}), 400
        images = body.get("images")
        if images is None and isinstance(body.get("image"), str):
            images = [body["image"]]
        if (
            not isinstance(images, list)
            or not images
            or not all(isinstance(image, str) and image for image in images)
        ):
            return jsonify({"error": "JSON field 'images' must contain frames"}), 400
        try:
            return jsonify(service.analyze(images)), 200
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "request exceeds the 7 MB limit"}), 413

    return app
