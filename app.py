"""Development entry point for the ACFM-Net backend."""

import os

from acfm_net.api import create_app

model_path = os.environ.get("ACFM_MODEL_PATH", "models/fatigue.joblib")
try:
    app = create_app(model_path)
except (FileNotFoundError, ValueError) as error:
    raise SystemExit(
        f"ACFM model is unavailable: {error}. "
        "Train one with python -m acfm_net.training first.",
    ) from error


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
