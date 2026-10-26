"""Summarize a local Edge Impulse annotation manifest."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

REQUIRED_COLUMNS = {
    "split",
    "subject_id",
    "open_eye_count",
    "closed_eye_count",
    "not_yawning_count",
    "yawning_count",
}


def summarize_manifest(path: Path) -> dict[str, object]:
    """Return counts and annotation prevalence without reading image data."""
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("manifest contains no rows")
    missing = sorted(REQUIRED_COLUMNS - set(rows[0]))
    if missing:
        raise ValueError(f"manifest is missing required columns: {', '.join(missing)}")

    def count(column: str) -> int:
        return sum(int(row[column]) for row in rows)

    return {
        "manifest": str(path),
        "rows": len(rows),
        "splits": dict(Counter(row["split"] for row in rows)),
        "subjects": sorted({row["subject_id"] for row in rows}),
        "annotation_counts": {
            "mata_terbuka": count("open_eye_count"),
            "mata_terpejam": count("closed_eye_count"),
            "tidak_menguap": count("not_yawning_count"),
            "menguap": count("yawning_count"),
        },
        "image_prevalence": {
            "has_closed_eye": sum(int(row["closed_eye_count"]) > 0 for row in rows)
            / len(rows),
            "has_yawning": sum(int(row["yawning_count"]) > 0 for row in rows)
            / len(rows),
        },
        "warning": (
            "This is an annotation summary, not a validated fatigue evaluation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize_manifest(args.manifest)
    rendered = json.dumps(report, indent=2)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
