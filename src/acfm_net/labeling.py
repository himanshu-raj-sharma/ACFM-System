"""Create a direct alertness-labeling template from an annotation manifest."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

TEMPLATE_COLUMNS = (
    "image_path",
    "source_path",
    "split",
    "subject_id",
    "label",
    "label_notes",
)


def create_template(manifest_path: Path, output_path: Path) -> int:
    """Copy image identity fields and add blank direct-label fields."""
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"image_path", "source_path", "split", "subject_id"}
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else []))
        raise ValueError(f"manifest is missing required columns: {', '.join(missing)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "image_path": row["image_path"],
                    "source_path": row["source_path"],
                    "split": row["split"],
                    "subject_id": row["subject_id"],
                    "label": "",
                    "label_notes": "",
                },
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(f"created {create_template(args.manifest, args.output)} labeling rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
