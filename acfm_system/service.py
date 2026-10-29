"""Application service that connects vision signals to the fatigue model."""

from __future__ import annotations

import base64
import binascii
import threading
from dataclasses import asdict

import cv2
import numpy as np

from .features import FaceFeatureExtractor
from .model import FatigueModel
from .temporal import WINDOW_FRAME_COUNT, aggregate


class MonitoringService:
    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    MAX_IMAGE_WIDTH = 4096
    MAX_IMAGE_HEIGHT = 4096
    MAX_IMAGE_PIXELS = 8_000_000
    MIN_FACE_DETECTION_RATE = 0.75

    def __init__(self, model_path: str) -> None:
        self._extractor = FaceFeatureExtractor()
        self._model = FatigueModel.load(model_path)
        # OpenCV Haar cascade instances are not guaranteed thread-safe for
        # concurrent detectMultiScale calls; serialize frame extraction so
        # threaded servers (Flask dev, "gunicorn --threads N") stay correct.
        self._extract_lock = threading.Lock()

    def analyze(self, encoded_images: list[str]) -> dict[str, object]:
        if len(encoded_images) != WINDOW_FRAME_COUNT:
            raise ValueError(
                f"provide exactly {WINDOW_FRAME_COUNT} frames per analysis window",
            )
        with self._extract_lock:
            frames = [
                self._extractor.extract(self._decode_image(encoded_image))
                for encoded_image in encoded_images
            ]
        features = aggregate(frames)
        if features.face_detection_rate < self.MIN_FACE_DETECTION_RATE:
            raise ValueError(
                "face was not reliably detected across the analysis window",
            )
        prediction = self._model.predict(features.vector())
        return {
            "prediction": asdict(prediction),
            "features": asdict(features),
            "frames_analyzed": len(frames),
            "disclaimer": (
                "Assistive estimate only; not a medical diagnosis or safety guarantee."
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
        try:
            image = cv2.imdecode(
                np.frombuffer(raw, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
        except cv2.error as error:
            raise ValueError("image could not be decoded") from error
        if image is None:
            raise ValueError("image could not be decoded")
        height, width = image.shape[:2]
        if (
            width > MonitoringService.MAX_IMAGE_WIDTH
            or height > MonitoringService.MAX_IMAGE_HEIGHT
            or width * height > MonitoringService.MAX_IMAGE_PIXELS
        ):
            raise ValueError("image dimensions exceed the supported limit")
        return image
