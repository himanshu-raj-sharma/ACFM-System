"""Flask API for real-time ACFM frame analysis."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from .service import MonitoringService


def create_app(model_path: str | None = None) -> Flask:
    app = Flask(__name__)
    configured_path = model_path or os.environ.get("ACFM_MODEL_PATH")
    if not configured_path:
        raise RuntimeError(
            "ACFM_MODEL_PATH is required. Train a labelled model before starting.",
        )
    service = MonitoringService(configured_path)

    @app.get("/api/health")
    def health() -> tuple[object, int]:
        return jsonify({"status": "ok", "service": "acfm-net"}), 200

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

    return app
