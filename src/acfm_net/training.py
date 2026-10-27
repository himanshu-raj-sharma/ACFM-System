"""Reproducible training and evaluation for labelled ACFM feature data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold

from .model import FatigueModel
from .temporal import WINDOW_FRAME_COUNT

FEATURE_COLUMNS = (
    "eye_closure_rate",
    "longest_eye_closure",
    "mouth_opening_rate",
    "mouth_opening_peak",
    "brightness_mean",
    "brightness_std",
)
QUALITY_COLUMN = "face_detection_rate"
MIN_FACE_DETECTION_RATE = 0.75


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def read_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {*FEATURE_COLUMNS, QUALITY_COLUMN, "label", "subject_id"}
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else []))
        raise ValueError(
            f"dataset is missing required columns: {', '.join(missing)}",
        )
    for row_number, row in enumerate(rows, start=2):
        missing_values = [
            column for column in required if row.get(column) in (None, "")
        ]
        if missing_values:
            missing = ", ".join(sorted(missing_values))
            raise ValueError(f"dataset row {row_number} is missing: {missing}")
    try:
        features = np.array(
            [[float(row[column]) for column in FEATURE_COLUMNS] for row in rows],
            dtype=np.float32,
        )
        quality = np.array(
            [float(row[QUALITY_COLUMN]) for row in rows],
            dtype=np.float32,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("feature and quality values must be numeric") from error
    if not np.isfinite(features).all() or not np.isfinite(quality).all():
        raise ValueError("feature and quality values must be finite")
    if (features < 0).any() or (features > 1).any():
        raise ValueError("feature values must be between 0 and 1")
    if (quality < MIN_FACE_DETECTION_RATE).any() or (quality > 1).any():
        raise ValueError(
            f"{QUALITY_COLUMN} must be between {MIN_FACE_DETECTION_RATE} and 1",
        )
    labels = np.array([row["label"].strip() for row in rows])
    groups = np.array([row["subject_id"].strip() for row in rows])
    if not all(labels) or not all(groups):
        raise ValueError("label and subject_id values cannot be empty")
    if set(labels) != {"alert", "fatigued"}:
        raise ValueError("labels must be exactly 'alert' and 'fatigued'")
    return features, labels, groups


def evaluate(
    features: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    folds: int,
) -> dict[str, object]:
    if folds < 2:
        raise ValueError("at least two evaluation folds are required")
    unique_groups = np.unique(groups)
    if len(unique_groups) < folds:
        raise ValueError(f"at least {folds} unique subjects are required")
    subject_counts = {
        label: len(set(groups[labels == label])) for label in ("alert", "fatigued")
    }
    if min(subject_counts.values()) < folds:
        raise ValueError(
            "each label must occur for at least one subject in every fold; "
            f"found {subject_counts}",
        )
    splitter = StratifiedGroupKFold(
        n_splits=folds,
        shuffle=True,
        random_state=42,
    )
    predictions = np.empty_like(labels)
    probabilities = np.zeros(len(labels), dtype=np.float32)
    fold_reports: list[dict[str, object]] = []
    for fold, (train_indices, test_indices) in enumerate(
        splitter.split(features, labels, groups),
        start=1,
    ):
        if set(labels[train_indices]) != {"alert", "fatigued"}:
            raise ValueError(f"fold {fold} training set does not contain both labels")
        if set(labels[test_indices]) != {"alert", "fatigued"}:
            raise ValueError(f"fold {fold} test set does not contain both labels")
        model = FatigueModel()
        model.fit(features[train_indices], labels[train_indices])
        predictions[test_indices] = model.predict_labels(features[test_indices])
        probabilities[test_indices] = model.predict_fatigued_probability(
            features[test_indices],
        )
        fold_reports.append(
            {
                "fold": fold,
                "test_subjects": sorted(set(groups[test_indices])),
                "rows": len(test_indices),
            },
        )
    report = classification_report(
        labels,
        predictions,
        labels=("alert", "fatigued"),
        output_dict=True,
        zero_division=0,
    )
    return {
        "folds": fold_reports,
        "classification_report": report,
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "roc_auc": float(roc_auc_score(labels == "fatigued", probabilities)),
        "confusion_matrix": confusion_matrix(
            labels,
            predictions,
            labels=("alert", "fatigued"),
        ).tolist(),
    }


def train(
    dataset_path: Path,
    output_path: Path,
    metadata_path: Path,
    folds: int = 5,
) -> dict[str, object]:
    features, labels, groups = read_dataset(dataset_path)
    if len(features) < 10:
        raise ValueError("at least 10 labelled rows are required")
    evaluation = evaluate(features, labels, groups, folds)
    model = FatigueModel()
    model.fit(features, labels)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_path)
    evaluation["feature_columns"] = FEATURE_COLUMNS
    evaluation["rows"] = len(features)
    evaluation["subjects"] = sorted(set(groups))
    evaluation["model_path"] = output_path.name
    evaluation["dataset_path"] = dataset_path.name
    evaluation["dataset_sha256"] = _sha256(dataset_path)
    evaluation["model_sha256"] = _sha256(output_path)
    evaluation["quality_column"] = QUALITY_COLUMN
    evaluation["window_frame_count"] = WINDOW_FRAME_COUNT
    evaluation["runtime"] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "acfm_net": _package_version("acfm-net"),
        "numpy": _package_version("numpy"),
        "opencv-python-headless": _package_version("opencv-python-headless"),
        "scikit-learn": _package_version("scikit-learn"),
    }
    metadata_path.write_text(
        json.dumps(evaluation, indent=2),
        encoding="utf-8",
    )
    return evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()
    print(
        json.dumps(
            train(args.data, args.output, args.metadata, folds=args.folds),
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
