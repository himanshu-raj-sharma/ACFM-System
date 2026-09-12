# Release checklist

## Data and model

- [ ] Dataset license and label mapping are recorded.
- [ ] No raw data or biometric derivatives are tracked by Git.
- [ ] Dataset has subject/session-disjoint folds.
- [ ] Evaluation report includes balanced accuracy, ROC-AUC, per-class recall,
      and confusion matrix.
- [ ] Model artifact and metadata use the same six-feature schema.
- [ ] Failure cases are reviewed across representative conditions.

## Application and privacy

- [ ] Camera consent is visible and required.
- [ ] Frames are processed in memory and never persisted.
- [ ] `ACFM_ALLOWED_ORIGIN` is set to the exact production frontend origin.
- [ ] HTTPS is used outside localhost.
- [ ] Logs do not contain image payloads or biometric data.
- [ ] Retention and deletion behavior is documented.
- [ ] The system is not marketed as a medical or safety decision tool.

## Verification

```powershell
python -m ruff format --check .
python -m ruff check .
python -m pytest
node --check .\server.js
node --check .\web\app.js
```
