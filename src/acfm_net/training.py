"""Reproducible training and evaluation for labelled ACFM feature data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from .model import FatigueModel

FEATURE_COLUMNS = ("eye_closure", "mouth_opening", "brightness")


def read_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {*FEATURE_COLUMNS, "label"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(
            f"dataset must contain columns: {', '.join((*FEATURE_COLUMNS, 'label'))}",
        )
    features = np.array(
        [[float(row[column]) for column in FEATURE_COLUMNS] for row in rows],
        dtype=np.float32,
    )
    labels = np.array([row["label"].strip() for row in rows])
    return features, labels


def train(dataset_path: Path, output_path: Path) -> str:
    features, labels = read_dataset(dataset_path)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    model = FatigueModel()
    model.fit(x_train, y_train)
    report = classification_report(y_test, model._model.predict(x_test))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(train(args.data, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
