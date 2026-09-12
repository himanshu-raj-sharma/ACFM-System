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
        return cls(model=load(path))

    def fit(self, features: np.ndarray, labels: np.ndarray) -> None:
        if len(features) < 10:
            raise ValueError("at least 10 labelled samples are required")
        if len(np.unique(labels)) != 2:
            raise ValueError("training data must contain exactly two classes")
        self._model.fit(features, labels)

    def save(self, path: str) -> None:
        dump(self._model, path)

    def predict(self, features: np.ndarray) -> FatiguePrediction:
        probabilities = self._model.predict_proba(features.reshape(1, -1))[0]
        score = float(probabilities[1])
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
