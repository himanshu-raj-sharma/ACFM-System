"""Flask API for real-time ACFM frame analysis."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .service import MonitoringService
from .temporal import WINDOW_FRAME_COUNT

# Optional: Prometheus metrics exporter. If unavailable, metrics endpoint is skipped.
try:
    from prometheus_flask_exporter import PrometheusMetrics
    _PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _PROMETHEUS_AVAILABLE = False

# Logging configuration belongs to the entry point (app.py); this module only
# obtains its namespaced logger so it never hijacks the host process setup.
logger = logging.getLogger("acfm-net")


def create_app(
    model_path: str | None = None,
    web_dir: str | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 7 * 1024 * 1024

    # Optional Prometheus metrics at /metrics (if observability extra installed)
    if _PROMETHEUS_AVAILABLE:
        PrometheusMetrics(app, defaults_prefix="acfm_net")
        logger.info("Prometheus metrics enabled at /metrics")

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
        g.request_id = uuid.uuid4().hex[:12]
        logger.info(
            "Request[%s]: %s %s from %s",
            g.request_id,
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
    # CSP is emitted as a response header (a static meta tag cannot know the
    # configured API origin). Extra API origins can be appended with
    # ACFM_CSP_CONNECT_SRC when the API is not same-origin.
    connect_sources = [
        "'self'",
        *os.environ.get("ACFM_CSP_CONNECT_SRC", "").split(),
    ]
    content_security_policy = "; ".join(
        [
            "default-src 'self'",
            "base-uri 'none'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: blob:",
            f"connect-src {' '.join(connect_sources)}",
        ],
    )
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
                    "model_loaded": service.ready,
                    "frames_required": WINDOW_FRAME_COUNT,
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
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = content_security_policy
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        # API payloads and HTML must never be cached; static assets revalidate
        # via ETag/Last-Modified (send_file sets those) instead of being
        # re-downloaded from scratch on every poll.
        if request.path.startswith("/api/") or response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Cache-Control"] = "no-cache"
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
                "Analysis[%s] completed: label=%s score=%.3f frames=%d",
                g.request_id,
                result["prediction"]["label"],
                result["prediction"]["score"],
                result["frames_analyzed"],
            )
            return jsonify(result), 200
        except ValueError as error:
            logger.warning("Analysis[%s] failed: %s", g.request_id, error)
            return jsonify({"error": str(error)}), 400
        except Exception as error:
            logger.error(
                "Analysis[%s] unexpected error: %s",
                g.request_id,
                error,
                exc_info=True,
            )
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
        logger.warning(
            "Rate limit[%s] exceeded for IP: %s",
            getattr(g, "request_id", "-"),
            request.remote_addr,
        )
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
            "Internal error[%s] from %s: %s",
            getattr(g, "request_id", "-"),
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
