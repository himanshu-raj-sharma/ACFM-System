"""Application service that connects vision signals to the fatigue model."""

from __future__ import annotations

import base64
import binascii
from dataclasses import asdict

import cv2
import numpy as np

from .features import FaceFeatureExtractor
from .model import FatigueModel


class MonitoringService:
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    def __init__(self, model_path: str) -> None:
        self._extractor = FaceFeatureExtractor()
        self._model = FatigueModel.load(model_path)

    def analyze(self, encoded_image: str) -> dict[str, object]:
        image = self._decode_image(encoded_image)
        features = self._extractor.extract(image)
        prediction = self._model.predict(features.vector())
        return {
            "prediction": asdict(prediction),
            "features": asdict(features),
            "disclaimer": (
                "Demo signal only; not a medical diagnosis or safety guarantee."
            ),
        }

    @staticmethod
    def _decode_image(encoded_image: str) -> np.ndarray:
        payload = encoded_image.split(",", 1)[-1]
        try:
            raw = base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("image must be valid base64 data") from error
        if len(raw) > MonitoringService.MAX_IMAGE_BYTES:
            raise ValueError("image exceeds the 5 MB limit")
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("image could not be decoded")
        return image
