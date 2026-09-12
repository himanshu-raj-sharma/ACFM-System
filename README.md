# ACFM-Net

ACFM-Net is an Adaptive Cognitive and Fatigue Monitoring System. It uses a
webcam frame, OpenCV face/eye signals, and a trainable MLP classifier to
estimate alertness in real time through a Flask API and browser interface.

The application refuses to start without a model trained from labelled data.
This is intentional: an unvalidated synthetic model is not an acceptable
production substitute.

## Requirements

- Python 3.10 or newer

## Installation

Create and activate a virtual environment, then install the project with its
development dependencies:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"
```

## Train a model from labelled data

Prepare a CSV with these columns:

```text
eye_closure,mouth_opening,brightness,label
0.0,0.1,0.8,alert
1.0,0.7,0.4,fatigued
```

The labels and features must come from an approved, documented dataset. Train
and evaluate the model:

```bash
python -m acfm_net.training --data data/features.csv --output models/fatigue.joblib
```

Review the printed hold-out classification report before deployment. Keep the
dataset, preprocessing, model artifact, metrics, and dataset license together
for reproducibility.

## Run the complete system

Terminal 1, backend:

```bash
python app.py
```

Terminal 2, frontend:

```bash
npm start
```

If the model is stored elsewhere, set `ACFM_MODEL_PATH` before starting the
backend. The backend will fail fast if the artifact is missing or invalid.

Open <http://127.0.0.1:3000>, allow camera access, and select **Analyze frame**.
The frontend sends a frame to `POST /api/analyze`; the backend also exposes
`GET /api/health`.

For a quick package check:

```bash
python -m acfm_net --version
```

## Development

Run the test suite and quality checks locally:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

The same checks run automatically in GitHub Actions for pushes and pull
requests.

## Project layout

```text
app.py              Backend entry point
src/acfm_net/       Feature extraction, model, and API
web/                Browser frontend
tests/              Automated tests
server.js           Frontend development server
pyproject.toml      Build, dependency, and tool configuration
.github/workflows/  Continuous integration
```

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).