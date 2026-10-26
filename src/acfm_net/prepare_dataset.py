"""Prepare fixed-size labeled windows from the direct-review CSV."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from collections import defaultdict
from pathlib import Path

from .temporal import WINDOW_FRAME_COUNT

FRAME_NUMBER = re.compile(r"frame_(?P<number>\d+)", re.IGNORECASE)
REQUIRED_COLUMNS = {"image_path", "source_path", "split", "subject_id", "label"}
LABELS = {"alert", "fatigued"}


def _frame_number(row: dict[str, str]) -> int:
    for value in (row["image_path"], row["source_path"]):
        match = FRAME_NUMBER.search(value)
        if match:
            return int(match.group("number"))
    raise ValueError(f"could not determine frame number for {row['image_path']}")


def _image_index(images_dir: Path) -> tuple[dict[str, Path], dict[str, list[Path]]]:
    by_relative: dict[str, Path] = {}
    by_name: dict[str, list[Path]] = defaultdict(list)
    for path in images_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(images_dir).as_posix().lower()
        by_relative[relative] = path
        by_name[path.name.lower()].append(path)
    return by_relative, by_name


def _locate_image(
    row: dict[str, str],
    images_dir: Path,
    by_relative: dict[str, Path],
    by_name: dict[str, list[Path]],
) -> Path:
    for value in (row["image_path"], row["source_path"]):
        normalized = value.replace("\\", "/").lstrip("/").lower()
        if normalized in by_relative:
            return by_relative[normalized]
    candidates = by_name.get(Path(row["source_path"]).name.lower(), [])
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"image was not found under {images_dir}: {row['image_path']}")
    raise ValueError(f"image filename is ambiguous: {row['source_path']}")


def prepare_dataset(
    labels_path: Path,
    images_dir: Path,
    output_dir: Path,
) -> int:
    """Copy homogeneous labeled windows into the extractor's raw layout."""
    with labels_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("labels CSV contains no rows")
    missing = sorted(REQUIRED_COLUMNS - set(rows[0]))
    if missing:
        raise ValueError(f"labels CSV is missing columns: {', '.join(missing)}")

    by_relative, by_name = _image_index(images_dir)
    grouped: dict[tuple[str, str], list[tuple[int, dict[str, str], Path]]] = (
        defaultdict(
            list,
        )
    )
    for row in rows:
        label = row["label"].strip()
        subject = row["subject_id"].strip()
        if label not in LABELS or not subject:
            raise ValueError("each row must have a valid label and subject_id")
        image = _locate_image(row, images_dir, by_relative, by_name)
        grouped[(subject, row["split"].strip())].append(
            (_frame_number(row), row, image),
        )

    windows = 0
    for (subject, split), items in sorted(grouped.items()):
        items.sort(key=lambda item: (item[0], item[2].name))
        for start in range(0, len(items) - WINDOW_FRAME_COUNT + 1, WINDOW_FRAME_COUNT):
            window = items[start : start + WINDOW_FRAME_COUNT]
            labels = {item[1]["label"].strip() for item in window}
            if len(labels) != 1:
                raise ValueError(
                    f"mixed labels in {subject}/{split} window starting at "
                    f"frame {window[0][0]}; label complete windows consistently",
                )
            label = labels.pop()
            window_id = (
                f"{split or 'unsplit'}-window-{start // WINDOW_FRAME_COUNT + 1:04d}"
            )
            destination = output_dir / label / subject / window_id
            destination.mkdir(parents=True, exist_ok=True)
            for _number, _row, image in window:
                shutil.copy2(image, destination / image.name)
            windows += 1
    if not windows:
        raise ValueError(
            f"no complete {WINDOW_FRAME_COUNT}-frame labeled windows were found",
        )
    return windows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = prepare_dataset(args.labels, args.images, args.output)
    print(f"prepared {count} labeled windows under {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
