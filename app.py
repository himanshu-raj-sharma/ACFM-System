"""Development entry point for the ACFM-Net backend."""

import os

from acfm_net.api import create_app

model_path = os.environ.get("ACFM_MODEL_PATH", "models/fatigue.joblib")
app = create_app(model_path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
