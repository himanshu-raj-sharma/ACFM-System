# ACFM-System

ACFM is an Adaptive Cognitive and Fatigue Monitoring System. It uses a short
webcam frame window, OpenCV face/eye signals, temporal behavior features, and a
trainable ACFM-Net classifier to estimate alertness through a Flask API and
browser interface.

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

Download the [Annotated Drowsiness Detection Dataset captured using Raspberry
Pi 5](https://data.mendeley.com/datasets/chvz7vh2dc/1) directly from Mendeley
Data. It is licensed CC BY 4.0; keep the attribution and license notice with
your local copy. Do not commit the dataset, face images, extracted artifacts,
or trained models to this repository.

Arrange a licensed local image subset as:

```text
data/raw/
  alert/
    subject-001/frame-001.jpg
  fatigued/
    subject-002/frame-001.jpg
```

Extract the same temporal feature schema used by the API. All frames for each
`label/subject_id` pair are aggregated into one window-level row:

```bash
python -m acfm_net.extract --input data/raw --output data/features.csv
```

Review the generated CSV. Its columns are:

```text
eye_closure_rate,longest_eye_closure,mouth_opening_rate,mouth_opening_peak,brightness_mean,brightness_std,label,subject_id
0.0,0.0,0.0,0.1,0.8,0.02,alert,subject-001
1.0,0.8,0.7,0.9,0.4,0.10,fatigued,subject-002
```

The directory labels are project labels and must be mapped to the source
dataset's original labels. Do not silently equate “closed eyes” with
clinically validated fatigue. Train and evaluate the model:

```bash
python -m acfm_net.training --data data/features.csv `
  --output models/fatigue.joblib `
  --metadata models/fatigue.metadata.json `
  --folds 5
```

The evaluator uses five subject-disjoint folds, not a random frame split, to
prevent identity leakage. It writes classification metrics, balanced accuracy,
ROC-AUC, confusion matrix, and fold subject IDs to the metadata report. Review
these metrics and class-specific recall before deployment; no accuracy target
is assumed to be safe without domain validation. Keep the dataset,
preprocessing, model artifact, metrics, and dataset license together for
reproducibility.

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
The frontend captures a short frame window and sends it to `POST /api/analyze`;
the backend also exposes `GET /api/health`.

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
src/acfm_net/       Features, temporal aggregation, model, extraction, API
data/               Local-only dataset files (never committed)
models/             Local-only trained artifacts (never committed)
web/                Browser frontend
tests/              Automated tests
server.js           Frontend development server
pyproject.toml      Build, dependency, and tool configuration
.github/workflows/  Continuous integration
```

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).