"""Temporal aggregation of frame-level vision signals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .features import FrameFeatures


@dataclass(frozen=True)
class TemporalFeatures:
    """Window-level features used by the fatigue model."""

    eye_closure_rate: float
    longest_eye_closure: float
    mouth_opening_rate: float
    mouth_opening_peak: float
    brightness_mean: float
    brightness_std: float

    def vector(self) -> np.ndarray:
        return np.array(
            [
                self.eye_closure_rate,
                self.longest_eye_closure,
                self.mouth_opening_rate,
                self.mouth_opening_peak,
                self.brightness_mean,
                self.brightness_std,
            ],
            dtype=np.float32,
        )


def aggregate(frames: list[FrameFeatures]) -> TemporalFeatures:
    """Aggregate at least one frame into stable window-level signals."""
    if not frames:
        raise ValueError("at least one frame is required")
    eyes = np.array([frame.eye_closure for frame in frames], dtype=np.float32)
    mouths = np.array([frame.mouth_opening for frame in frames], dtype=np.float32)
    brightness = np.array(
        [frame.brightness for frame in frames],
        dtype=np.float32,
    )
    longest = 0
    current = 0
    for closed in eyes >= 0.5:
        current = current + 1 if closed else 0
        longest = max(longest, current)
    return TemporalFeatures(
        eye_closure_rate=float(np.mean(eyes)),
        longest_eye_closure=float(longest / len(frames)),
        mouth_opening_rate=float(np.mean(mouths >= 0.5)),
        mouth_opening_peak=float(np.max(mouths)),
        brightness_mean=float(np.mean(brightness)),
        brightness_std=float(np.std(brightness)),
    )
