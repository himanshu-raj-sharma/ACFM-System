"""Computer-vision feature extraction for ACFM demo frames."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FrameFeatures:
    """Numerical signals consumed by the fatigue classifier."""

    face_detected: bool
    eye_closure: float
    mouth_opening: float
    brightness: float

    def vector(self) -> np.ndarray:
        return np.array(
            [self.eye_closure, self.mouth_opening, self.brightness],
            dtype=np.float32,
        )


class FaceFeatureExtractor:
    """Extract stable, low-cost fatigue signals from a BGR image."""

    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades
        self._faces = self._classifier(
            cascade_path + "haarcascade_frontalface_default.xml",
        )
        self._eyes = self._classifier(cascade_path + "haarcascade_eye.xml")

    @staticmethod
    def _classifier(path: str):
        """Load Haar cascades when supported by the installed OpenCV build."""
        classifier_type = getattr(cv2, "CascadeClassifier", None)
        if classifier_type is None:
            return None
        classifier = classifier_type(path)
        return None if classifier.empty() else classifier

    def extract(self, image: np.ndarray) -> FrameFeatures:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray) / 255.0)
        if self._faces is None or self._eyes is None:
            return FrameFeatures(False, 0.0, 0.0, brightness)
        faces = self._faces.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )
        if len(faces) == 0:
            return FrameFeatures(False, 1.0, 0.0, brightness)

        x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
        face_gray = gray[y : y + height, x : x + width]
        eyes = self._eyes.detectMultiScale(
            face_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20),
        )
        eye_closure = 0.0 if len(eyes) >= 2 else 1.0
        lower_face = face_gray[int(height * 0.55) :]
        mouth_opening = self._mouth_signal(lower_face)
        return FrameFeatures(True, eye_closure, mouth_opening, brightness)

    @staticmethod
    def _mouth_signal(region: np.ndarray) -> float:
        if region.size == 0:
            return 0.0
        dark_pixels = np.count_nonzero(region < 70)
        return float(np.clip(dark_pixels / region.size * 3.0, 0.0, 1.0))
