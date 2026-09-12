"""Flask API for real-time ACFM frame analysis."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from .service import MonitoringService


def create_app(model_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 7 * 1024 * 1024
    allowed_origin = os.environ.get("ACFM_ALLOWED_ORIGIN", "http://127.0.0.1:3000")
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
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Vary"] = "Origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/analyze")
    def analyze() -> tuple[object, int]:
        body = request.get_json(silent=True) or {}
        image = body.get("image")
        if not isinstance(image, str) or not image:
            return jsonify({"error": "JSON field 'image' is required"}), 400
        try:
            return jsonify(service.analyze(image)), 200
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "request exceeds the 7 MB limit"}), 413

    return app
