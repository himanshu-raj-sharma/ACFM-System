"""Flask API for real-time ACFM frame analysis."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .service import MonitoringService

# Logging configuration belongs to the entry point (app.py); this module only
# obtains its namespaced logger so it never hijacks the host process setup.
logger = logging.getLogger("acfm-net")


def create_app(
    model_path: str | None = None,
    web_dir: str | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 7 * 1024 * 1024

    # Rate limiting: per-IP limits apply only to explicitly decorated routes.
    # No global default limits: otherwise the shared daily budget throttles
    # /api/health probes and static asset requests (a restart-loop risk).
    # Behind a trusted proxy, derive the client IP with ProxyFix instead.
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri="memory://",
    )

    @app.before_request
    def log_request():
        logger.info(
            "Request: %s %s from %s",
            request.method,
            request.path,
            request.remote_addr,
        )

    allowed_origin = os.environ.get(
        "ACFM_ALLOWED_ORIGIN",
        "http://127.0.0.1:3000,http://localhost:3000",
    )
    allowed_origins = {
        origin.strip() for origin in allowed_origin.split(",") if origin.strip()
    }
    configured_path = model_path or os.environ.get("ACFM_MODEL_PATH")
    if not configured_path:
        raise RuntimeError(
            "ACFM_MODEL_PATH is required. Train a labelled model before starting.",
        )
    service = MonitoringService(configured_path)
    frontend_root = Path(web_dir or os.environ.get("ACFM_WEB_DIR", "web")).resolve()

    def origin_is_allowed() -> bool:
        # Strict allowlist only. This previously also accepted any request
        # whose Origin matched the Host header, which let clients bypass the
        # configured origins via host-header injection.
        return request.headers.get("Origin") in allowed_origins

    @app.get("/api/health")
    def health() -> tuple[object, int]:
        logger.info("Health check requested from %s", request.remote_addr)
        return (
            jsonify(
                {
                    "status": "ok",
                    "service": "acfm-net",
                    "model_loaded": True,
                    "privacy": {
                        "frames_persisted": False,
                        "consent_required": True,
                    },
                }
            ),
            200,
        )

    # Health probes must never consume (or be throttled by) the API budget.
    limiter.exempt(health)

    @app.after_request
    def add_security_headers(response):
        origin = request.headers.get("Origin")
        if origin_is_allowed():
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
        origin = request.headers.get("Origin")
        logger.info("CORS preflight check from origin: %s", origin)
        if not origin_is_allowed():
            logger.warning("Rejected OPTIONS request from origin: %s", origin)
            return jsonify({"error": "origin is not allowed"}), 403
        return "", 204

    @app.post("/api/analyze")
    @limiter.limit("60 per minute")
    def analyze() -> tuple[object, int]:
        if not origin_is_allowed():
            origin = request.headers.get("Origin")
            logger.warning("Rejected analyze request from origin: %s", origin)
            return jsonify({"error": "origin is not allowed"}), 403
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
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
            result = service.analyze(images)
            logger.info(
                "Analysis completed: label=%s score=%.3f frames=%d",
                result["prediction"]["label"],
                result["prediction"]["score"],
                result["frames_analyzed"],
            )
            return jsonify(result), 200
        except ValueError as error:
            logger.warning("Analysis failed: %s", error)
            return jsonify({"error": str(error)}), 400
        except Exception as error:
            logger.error("Unexpected error during analysis: %s", error, exc_info=True)
            return jsonify({"error": "internal server error"}), 500

    @app.errorhandler(413)
    def request_too_large(_error):
        logger.warning(
            "Request too large from %s: %s bytes",
            request.remote_addr,
            request.content_length,
        )
        return jsonify({"error": "request exceeds the 7 MB limit"}), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(_error):
        logger.warning("Rate limit exceeded for IP: %s", request.remote_addr)
        response = jsonify({"error": "rate limit exceeded. Try again later."})
        response.headers["Retry-After"] = "10"
        return response, 429

    @app.errorhandler(400)
    def bad_request(_error):
        logger.warning("Bad request from %s: %s", request.remote_addr, _error)
        return jsonify({"error": "request was invalid"}), 400

    @app.errorhandler(500)
    def internal_error(_error):
        logger.error(
            "Internal server error from %s: %s",
            request.remote_addr,
            _error,
            exc_info=True,
        )
        return jsonify({"error": "internal server error"}), 500

    if frontend_root.is_dir():

        @app.get("/")
        def frontend_index():
            return send_from_directory(frontend_root, "index.html")

        @app.get("/<path:filename>")
        def frontend_asset(filename: str):
            return send_from_directory(frontend_root, filename)

    return app
