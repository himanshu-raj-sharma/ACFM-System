# Dataset and model release policy

ACFM-System does not redistribute biometric data. The repository contains only
code and documentation; local datasets and trained artifacts are ignored by
Git.

## Recommended source

The initial supported source is the [Annotated Drowsiness Detection Dataset
Captured Using Raspberry Pi 5](https://data.mendeley.com/datasets/chvz7vh2dc/1).
The source record identifies the dataset as **CC BY 4.0**. Download it directly
from the source record, retain its attribution and license notice, and verify
the current terms before each redistribution or commercial use.

Other datasets must not be added until their provider explicitly permits the
intended use. In particular, do not publish raw videos, face crops, screenshots,
landmarks, embeddings, or other biometric derivatives from restricted datasets.

## Required local layout

```text
data/raw/<label>/<subject_id>/<frame>.<extension>
```

`<label>` must be exactly `alert` or `fatigued` after a documented mapping from
the source dataset. A source label such as “closed eyes” is not automatically
equivalent to clinical fatigue. Record the mapping, source version, download
date, license, and any exclusions in your local experiment notes.

## Release gate

Before using a model outside a local research environment, retain:

- Dataset source, version, license, and label mapping.
- Subject-disjoint cross-validation report.
- Per-class recall, balanced accuracy, ROC-AUC, and confusion matrix.
- Model artifact hash and feature schema.
- Known failure cases across lighting, pose, eyewear, skin tone, and camera type.
- Consent, retention, deletion, and incident-response procedures.

No model may be described as clinically validated, safety-critical, or suitable
for employment, driving, or medical decisions from this repository alone.
