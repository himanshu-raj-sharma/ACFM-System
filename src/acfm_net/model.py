"""Trainable fatigue classifier with persisted model artifacts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from joblib import dump, load
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class FatiguePrediction:
    """Human-readable model output."""

    label: str
    score: float
    recommendation: str


class FatigueModel:
    """Small MLP trained on labelled feature data.

    The model must be trained on labelled data before it is used for research
    or clinical decisions.
    """

    def __init__(self, model=None) -> None:
        self._model = make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=(12, 8),
                max_iter=1000,
                random_state=42,
            ),
        )
        if model is not None:
            self._model = model

    @classmethod
    def load(cls, path: str) -> FatigueModel:
        model = load(path)
        if not hasattr(model, "predict_proba") or not hasattr(model, "n_features_in_"):
            raise ValueError("model artifact is not a compatible probability model")
        if model.n_features_in_ != 6:
            raise ValueError("model artifact must accept exactly six features")
        return cls(model=model)

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        if len(features) < 4:
            raise ValueError("at least four labelled samples are required")
        if set(np.unique(labels)) != {"alert", "fatigued"}:
            raise ValueError("labels must be exactly 'alert' and 'fatigued'")
        counts = {label: int(np.sum(labels == label)) for label in np.unique(labels)}
        target_count = max(counts.values())
        rng = np.random.default_rng(42)
        balanced_indices = np.concatenate(
            [
                rng.choice(
                    np.flatnonzero(labels == label),
                    size=target_count,
                    replace=True,
                )
                for label in sorted(counts)
            ],
        )
        self._model.fit(features[balanced_indices], labels[balanced_indices])

    def save(self, path: str) -> None:
        dump(self._model, path)

    def predict(self, features: np.ndarray) -> FatiguePrediction:
        if features.shape != (6,):
            raise ValueError("prediction requires exactly six feature values")
        probabilities = self._model.predict_proba(features.reshape(1, -1))[0]
        classes = list(self._model.classes_)
        fatigued_index = classes.index("fatigued") if "fatigued" in classes else 1
        score = float(probabilities[fatigued_index])
        if score >= 0.65:
            return FatiguePrediction(
                "fatigued",
                score,
                "Take a short break and reassess before continuing.",
            )
        if score >= 0.4:
            return FatiguePrediction(
                "alertness reduced",
                score,
                "Monitor your alertness and consider a short break.",
            )
        return FatiguePrediction("alert", score, "Alertness looks stable.")
