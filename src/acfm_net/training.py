"""Reproducible training and evaluation for labelled ACFM feature data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit

from .model import FatigueModel

FEATURE_COLUMNS = (
    "eye_closure_rate",
    "longest_eye_closure",
    "mouth_opening_rate",
    "mouth_opening_peak",
    "brightness_mean",
    "brightness_std",
)


def read_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {*FEATURE_COLUMNS, "label", "subject_id"}
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else []))
        raise ValueError(
            f"dataset is missing required columns: {', '.join(missing)}",
        )
    features = np.array(
        [[float(row[column]) for column in FEATURE_COLUMNS] for row in rows],
        dtype=np.float32,
    )
    labels = np.array([row["label"].strip() for row in rows])
    groups = np.array([row["subject_id"].strip() for row in rows])
    if not all(labels) or not all(groups):
        raise ValueError("label and subject_id values cannot be empty")
    if set(labels) != {"alert", "fatigued"}:
        raise ValueError("labels must be exactly 'alert' and 'fatigued'")
    return features, labels, groups


def train(dataset_path: Path, output_path: Path, metadata_path: Path) -> str:
    features, labels, groups = read_dataset(dataset_path)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_indices, test_indices = next(splitter.split(features, labels, groups))
    model = FatigueModel()
    model.fit(features[train_indices], labels[train_indices])
    predictions = model._model.predict(features[test_indices])
    report = classification_report(labels[test_indices], predictions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_path)
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": FEATURE_COLUMNS,
                "model_path": str(output_path),
                "train_rows": len(train_indices),
                "test_rows": len(test_indices),
                "test_subjects": sorted(set(groups[test_indices])),
                "classification_report": report,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    print(train(args.data, args.output, args.metadata))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
