"""Development entry point for the ACFM-Net backend."""

import os

from acfm_net.api import create_app
from acfm_net.artifact import ensure_model

model_path = os.environ.get("ACFM_MODEL_PATH", "models/fatigue.joblib")
try:
    ensure_model(model_path)
    app = create_app(model_path, os.environ.get("ACFM_WEB_DIR", "web"))
except (FileNotFoundError, RuntimeError, ValueError) as error:
    raise SystemExit(
        f"ACFM model is unavailable: {error}. "
        "Train one with python -m acfm_net.training first.",
    ) from error


if __name__ == "__main__":
    app.run(
        host=os.environ.get("ACFM_HOST", "127.0.0.1"),
        port=int(os.environ.get("ACFM_PORT", "5000")),
        debug=False,
    )
