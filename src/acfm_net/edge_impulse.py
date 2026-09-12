"""Convert Edge Impulse object annotations into an auditable CSV manifest."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
LABELS = ("mata_terbuka", "mata_terpejam", "tidak_menguap", "menguap")
SUBJECT_PATTERN = re.compile(r"^frame_\d+_(?P<subject>.+?)\.jpg$", re.IGNORECASE)

MANIFEST_COLUMNS = (
    "image_path",
    "source_path",
    "split",
    "subject_id",
    "open_eye_count",
    "closed_eye_count",
    "not_yawning_count",
    "yawning_count",
    "eye_annotation_count",
    "mouth_annotation_count",
    "source_labels",
)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _subject_id(name: str) -> str:
    match = SUBJECT_PATTERN.match(name)
    if match:
        return match.group("subject")
    stem = Path(name).stem
    return stem.split("_", 1)[-1] or "unknown"


def _annotation_labels(record: dict[str, Any]) -> list[str]:
    boxes = record.get("boundingBoxes", [])
    if isinstance(boxes, str):
        raise ValueError(f"boundingBoxes must be an array for {record.get('name', '')}")
    labels: list[str] = []
    for box in _as_list(boxes):
        if not isinstance(box, dict) or not str(box.get("label", "")).strip():
            raise ValueError(f"invalid bounding box in {record.get('name', '')}")
        labels.append(str(box["label"]).strip())
    return labels


def convert_labels(
    labels_path: Path,
    images_dir: Path,
    output_csv: Path,
    metadata_path: Path | None = None,
) -> int:
    """Write one manifest row per annotated image and return its row count."""
    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    records = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("labels JSON must contain a non-empty 'files' array")

    image_files = {
        path.name: path
        for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    }
    rows: list[dict[str, str]] = []
    label_counts: Counter[str] = Counter()
    missing: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each item in labels.files must be an object")
        name = str(record.get("name", "")).strip()
        source_path = str(record.get("path", "")).replace("\\", "/").strip()
        filename = Path(source_path).name or name
        image_path = image_files.get(filename) or image_files.get(name)
        if image_path is None:
            missing.append(filename)
            continue
        labels = _annotation_labels(record)
        counts = Counter(labels)
        label_counts.update(labels)
        rows.append(
            {
                "image_path": image_path.relative_to(images_dir).as_posix(),
                "source_path": source_path,
                "split": str(record.get("category", "")).strip().lower(),
                "subject_id": _subject_id(name or filename),
                "open_eye_count": str(counts["mata_terbuka"]),
                "closed_eye_count": str(counts["mata_terpejam"]),
                "not_yawning_count": str(counts["tidak_menguap"]),
                "yawning_count": str(counts["menguap"]),
                "eye_annotation_count": str(
                    counts["mata_terbuka"] + counts["mata_terpejam"],
                ),
                "mouth_annotation_count": str(
                    counts["tidak_menguap"] + counts["menguap"],
                ),
                "source_labels": ",".join(sorted(set(labels))),
            },
        )
    if missing:
        sample = ", ".join(missing[:3])
        raise ValueError(
            f"{len(missing)} annotated images were not found under "
            f"{images_dir}: {sample}",
        )
    if not rows:
        raise ValueError("no annotated images matched the images directory")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    if metadata_path is not None:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "labels_file": str(labels_path),
                    "images_directory": str(images_dir),
                    "rows": len(rows),
                    "splits": dict(Counter(row["split"] for row in rows)),
                    "subjects": sorted({row["subject_id"] for row in rows}),
                    "source_label_counts": dict(label_counts),
                    "source_labels": LABELS,
                    "warning": (
                        "This manifest contains eye/yawning annotations. "
                        "They are not direct alert/fatigued ground truth."
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    count = convert_labels(args.labels, args.images, args.output, args.metadata)
    print(f"converted {count} annotated images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
