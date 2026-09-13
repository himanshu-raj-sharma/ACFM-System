# ACFM-System

ACFM is an Adaptive Cognitive and Fatigue Monitoring System. It uses a short
webcam frame window, OpenCV face/eye signals, temporal behavior features, and a
trainable ACFM-Net classifier to estimate alertness through a Flask API and
browser interface.

The application refuses to start without a model trained from labelled data.
This is intentional: an unvalidated synthetic model is not an acceptable
production substitute.

The repository is complete as a reproducible application and training
pipeline, but it cannot include a trained model because model artifacts depend
on the licensed dataset you download locally. The release checklist identifies
the evidence required before claiming scientific or operational readiness.

## Requirements

- Python 3.10 or newer
- OpenCV 4.x (installed automatically by the project dependencies)

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

If the environment was installed before the OpenCV version constraint was
added, reinstall the compatible build:

```powershell
python -m pip install --force-reinstall "opencv-python-headless>=4.9,<5"
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

### Edge Impulse dataset conversion

The recommended Mendeley dataset is an Edge Impulse export. Its annotations
are stored in `modelling/info.labels`, while the extracted images are stored
under the `training` and `testing` directories. Convert them to an auditable
manifest without changing the original labels:

```powershell
python -m acfm_net.edge_impulse `
  --labels "$HOME\Downloads\ACFM-dataset\modelling\info.labels" `
  --images "$HOME\Downloads\ACFM-dataset\extracted" `
  --output data\edge_impulse_manifest.csv `
  --metadata data\edge_impulse_manifest.json
```

The manifest records the source split, subject identifier, original label
counts, and matched local image path. It is an eye/yawning annotation manifest,
not a fatigue-training dataset. A separate, documented alertness label source
is still required before running the `alert`/`fatigued` training command.

Generate a compact report for a presentation or experiment record:

```powershell
python -m acfm_net.dataset_report `
  --manifest data\edge_impulse_manifest.csv `
  --output data\edge_impulse_report.json
```

The report contains row counts, split and subject coverage, annotation totals,
and the proportion of images containing a closed-eye or yawning annotation.
It does not calculate fatigue accuracy because this dataset has no direct
`alert`/`fatigued` ground truth.

### Collect direct alertness labels

To train the fatigue classifier, create a labeling template:

```powershell
python -m acfm_net.labeling `
  --manifest data\edge_impulse_manifest.csv `
  --output data\alertness_labels.csv
```

Open `data\alertness_labels.csv` in a spreadsheet. Fill every `label` cell
with exactly `alert` or `fatigued`, and record the labeling rationale in
`label_notes`. Judge the complete short frame window, not an isolated blink:
`fatigued` should require an observable sustained drowsiness/fatigue state,
while `alert` should mean the person is attentive. Use at least two
independent labelers where possible, resolve disagreements before training,
and keep all rows for one subject in the same evaluation fold.

Do not infer the direct label mechanically from `mata_terpejam` or `menguap`;
those annotations may be useful evidence for a human labeler but are not
ground truth. Before training, ensure both `alert` and `fatigued` are present
for at least five subjects and convert the completed labels into the
feature CSV required by `acfm_net.training`.

For visual review, generate a local browser page with the original images and
annotation counts:

```powershell
python -m acfm_net.review_export `
  --manifest data\edge_impulse_manifest.csv `
  --images "$HOME\Downloads\ACFM-dataset\extracted" `
  --output data\review
```

Open `data\review\index.html` in a browser. Select a label and add notes for
each image, then use **Download completed labels CSV**. Copy the downloaded
`alertness_labels.csv` over `data\alertness_labels.csv` after reviewing it.

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
For deployment, set `ACFM_ALLOWED_ORIGIN` to the exact frontend origin; multiple
origins may be comma-separated. The API requires explicit consent, accepts only
the configured origin, limits request size, and does not write submitted
frames to disk.

Open <http://127.0.0.1:3000>, allow camera access, and select **Analyze frame**.
The frontend captures a short frame window after consent and sends it to
`POST /api/analyze`;
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

## Readiness and limitations

Use [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) before any release
and [docs/DATASET.md](docs/DATASET.md) for dataset licensing and privacy rules.
The repository is application-complete, but scientific readiness depends on
the locally supplied dataset, measured results, representative failure-case
review, and an appropriate governance process. The code does not establish
clinical validity.

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
docs/               Dataset policy and release checklist
```

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).