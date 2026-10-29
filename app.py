"""Development entry point for the ACFM-Net backend."""

import logging
import os

from acfm_net.api import create_app
from acfm_net.artifact import ensure_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

model_path = os.environ.get("ACFM_MODEL_PATH", "models/fatigue.joblib")
try:
    ensure_model(model_path)
    app = create_app(model_path, os.environ.get("ACFM_WEB_DIR", "web"))
# OSError covers network failures while downloading a model artifact
# (URLError, HTTPError, socket timeouts, TLS errors).
except (FileNotFoundError, RuntimeError, ValueError, OSError) as error:
    raise SystemExit(
        f"ACFM model is unavailable: {error}. "
        "Train one with python -m acfm_net.training first.",
    ) from error


if __name__ == "__main__":
    # Render, Heroku, Fly, Railway all inject PORT; ACFM_PORT is our legacy name.
    raw_port = os.environ.get("PORT") or os.environ.get("ACFM_PORT", "5000")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise SystemExit(
            f"PORT/ACFM_PORT must be an integer, got {raw_port!r}",
        ) from error

    app.run(
        host=os.environ.get("ACFM_HOST", "0.0.0.0"),
        port=port,
        debug=False,
    )
