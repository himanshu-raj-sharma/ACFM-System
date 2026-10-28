"""Create a local browser-based review page for direct alertness labels."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

REQUIRED_COLUMNS = (
    "image_path",
    "source_path",
    "split",
    "subject_id",
    "open_eye_count",
    "closed_eye_count",
    "not_yawning_count",
    "yawning_count",
)


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def create_review_page(
    manifest_path: Path,
    images_dir: Path,
    output_dir: Path,
) -> int:
    """Create HTML and a blank CSV copy for local human review."""
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("manifest contains no rows")
    missing = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing:
        raise ValueError(f"manifest is missing required columns: {', '.join(missing)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / "alertness_labels.csv"
    with labels_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "image_path",
                "source_path",
                "split",
                "subject_id",
                "label",
                "label_notes",
            ),
        )
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

    cards = []
    for index, row in enumerate(rows, start=1):
        image = images_dir / Path(row["image_path"])
        cards.append(
            f"""
<article class="card" data-index="{index}">
  <img src="{html.escape(_file_url(image))}" alt="Dataset image {index}">
  <div class="details">
    <strong>{index}. {html.escape(row["subject_id"])}</strong>
    <span>{html.escape(row["split"])}</span>
    <small>{html.escape(row["image_path"])}</small>
    <small>Open eyes: {row["open_eye_count"]} |
    Closed eyes: {row["closed_eye_count"]} |
    Not yawning: {row["not_yawning_count"]} |
    Yawning: {row["yawning_count"]}</small>
    <label>Label
      <select data-field="label">
        <option value="">Choose...</option>
        <option value="alert">alert</option>
        <option value="fatigued">fatigued</option>
      </select>
    </label>
    <label>Notes
      <input data-field="notes" placeholder="Reason for the label">
    </label>
  </div>
</article>"""
        )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ACFM alertness review</title>
<style>
body {{ font: 15px system-ui, sans-serif; margin: 1rem; background: #f3f4f6; }}
header {{ position: sticky; top: 0; background: white; padding: 1rem; z-index: 2; }}
button {{ padding: .6rem .9rem; margin-right: .5rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill,
  minmax(320px, 1fr)); gap: 1rem; }}
.card {{ background: white; border-radius: .5rem; overflow: hidden;
  box-shadow: 0 1px 4px #0002; }}
.card img {{ display: block; width: 100%; height: 220px;
  object-fit: contain; background: #111; }}
.details {{ display: grid; gap: .45rem; padding: .8rem; }}
small {{ overflow-wrap: anywhere; color: #555; }}
label {{ display: grid; gap: .2rem; }}
select, input {{ padding: .45rem; }}
</style>
</head>
<body>
<header>
  <h1>ACFM alertness review</h1>
  <p>Review the complete visual context. Do not infer fatigue from one blink
  or one annotation.</p>
  <button id="download">Download completed labels CSV</button>
  <span id="status"></span>
</header>
<main class="grid">{"".join(cards)}</main>
<script>
const rows = {
        json.dumps(
            [
                {
                    "image_path": row["image_path"],
                    "source_path": row["source_path"],
                    "split": row["split"],
                    "subject_id": row["subject_id"],
                }
                for row in rows
            ]
        )
    };
const cards = [...document.querySelectorAll(".card")];
function updateStatus() {{
  const done = cards.filter(card =>
    card.querySelector('[data-field="label"]').value).length;
  document.querySelector("#status").textContent =
    `${{done}} / ${{cards.length}} labeled`;
}}
cards.forEach(card => card.addEventListener("change", updateStatus));
document.querySelector("#download").addEventListener("click", () => {{
  const lines = ["image_path,source_path,split,subject_id,label,label_notes"];
  cards.forEach((card, index) => {{
    const label = card.querySelector('[data-field="label"]').value;
    const notes = card.querySelector('[data-field="notes"]').value;
    const row = rows[index];
    const values = [row.image_path, row.source_path, row.split,
      row.subject_id, label, notes];
    lines.push(values.map(value =>
      `"${{String(value).replaceAll('"', '""')}}"`).join(","));
  }});
  const blob = new Blob([lines.join("\\n")], {{type: "text/csv"}});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "alertness_labels.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}});
updateStatus();
</script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = create_review_page(args.manifest, args.images, args.output)
    print(f"created review page for {count} images: {args.output / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
