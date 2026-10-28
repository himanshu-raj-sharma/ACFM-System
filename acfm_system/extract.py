"""Extract model features from a local, licensed image dataset."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import cv2

from .features import FaceFeatureExtractor
from .temporal import WINDOW_FRAME_COUNT, aggregate


def extract_dataset(input_dir: Path, output_csv: Path) -> int:
    """Extract one row per fixed-size subject/label window."""
    extractor = FaceFeatureExtractor()
    grouped: dict[tuple[str, str, str], list] = defaultdict(list)
    for image_path in sorted(input_dir.rglob("*")):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            continue
        relative = image_path.relative_to(input_dir)
        if len(relative.parts) < 3:
            raise ValueError(
                "images must be under input/label/subject_id/image.ext",
            )
        label, subject_id = relative.parts[0:2]
        window_id = relative.parts[2] if len(relative.parts) >= 4 else "sequence"
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"could not decode image: {image_path}")
        grouped[(label, subject_id, window_id)].append(extractor.extract(image))

    rows: list[dict[str, str]] = []
    for (label, subject_id, window_id), frames in sorted(grouped.items()):
        if len(frames) < WINDOW_FRAME_COUNT:
            raise ValueError(
                f"{label}/{subject_id} contains {len(frames)} frames; "
                f"at least {WINDOW_FRAME_COUNT} are required",
            )
        for start in range(0, len(frames) - WINDOW_FRAME_COUNT + 1, WINDOW_FRAME_COUNT):
            window = frames[start : start + WINDOW_FRAME_COUNT]
            features = aggregate(window)
            if features.face_detection_rate < 0.75:
                raise ValueError(
                    f"face detection is insufficient for {label}/{subject_id} "
                    f"window starting at frame {start}",
                )
            rows.append(
                {
                    "eye_closure_rate": str(features.eye_closure_rate),
                    "longest_eye_closure": str(features.longest_eye_closure),
                    "mouth_opening_rate": str(features.mouth_opening_rate),
                    "mouth_opening_peak": str(features.mouth_opening_peak),
                    "brightness_mean": str(features.brightness_mean),
                    "brightness_std": str(features.brightness_std),
                    "face_detection_rate": str(features.face_detection_rate),
                    "window_id": window_id,
                    "label": label,
                    "subject_id": subject_id,
                },
            )
    if not rows:
        raise ValueError("no supported images found")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    columns = tuple(rows[0])
    with output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(f"extracted {extract_dataset(args.input, args.output)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
