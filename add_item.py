#!/usr/bin/env python3
"""Interactively add an artwork, process its media, and rebuild the website."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from media_tools import (
    IMAGE_EXTENSIONS,
    ROOT,
    VIDEO_EXTENSIONS,
    copy_media,
    optimize_image,
    optimize_video,
    relative_to_root,
    slugify,
)


def ask(label: str, *, required: bool = False, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("This field is required.")


def choose(label: str, options: list[tuple[str, str]]) -> str:
    print(f"\n{label}")
    for index, (_, name) in enumerate(options, 1):
        print(f"  {index}. {name}")
    while True:
        value = input("Choose a number: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(options):
            return options[int(value) - 1][0]
        print("Please enter one of the listed numbers.")


def parse_price(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.replace("$", "").replace(",", "").strip()
    price = float(cleaned)
    if price < 0:
        raise ValueError("Price cannot be negative")
    return price


def main() -> int:
    catalog_path = ROOT / "items.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    print("Add a new Kinetic Creations artwork\n")
    title = ask("Title", required=True)
    item_id = ask("URL-friendly ID", default=slugify(title))
    if not item_id or item_id != slugify(item_id):
        raise SystemExit("The ID must contain only lowercase letters, numbers, and hyphens.")
    if any(item["id"] == item_id for item in catalog["items"]):
        raise SystemExit(f"An item with ID '{item_id}' already exists.")

    categories = [(entry["id"], entry["name"]) for entry in catalog["categories"]]
    category = choose("Category", categories)
    description = ask("Description", required=True)
    price = parse_price(ask("Price in USD (leave blank for Contact for price)"))
    dimensions = ask("Dimensions (optional)") or None
    materials = ask("Materials (optional)") or None
    year_value = ask("Year (optional)")
    year = int(year_value) if year_value else None
    availability = choose(
        "Availability",
        [
            ("available", "Available"),
            ("inquire", "Availability on request"),
            ("made-to-order", "Made to order"),
            ("reserved", "Reserved"),
            ("sold", "Sold"),
        ],
    )
    featured = ask("Feature this work? (y/N)", default="n").lower().startswith("y")

    print("\nEnter image or video paths one at a time. Dragging files into the terminal also works.")
    print("Press Return on an empty line when finished.")
    source_paths: list[Path] = []
    while True:
        value = input("Media path: ").strip().strip("'").strip('"')
        if not value:
            break
        path = Path(value).expanduser()
        if not path.is_file():
            print("File not found. Try again.")
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            print("Unsupported file type. Use JPEG, PNG, WebP, MOV, MP4, M4V, or WebM.")
            continue
        source_paths.append(path)

    if not source_paths:
        raise SystemExit("At least one image or video is required.")

    media_records = []
    copied_files: list[Path] = []
    try:
        for sequence, source in enumerate(source_paths, 1):
            copied = copy_media(source, item_id, sequence)
            copied_files.append(copied)
            extension = copied.suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                optimize_image(copied, item_id)
            else:
                converted = optimize_video(copied, item_id)
                if converted is None:
                    print(f"Warning: using original video because conversion was unavailable: {copied.name}")
            media_records.append(
                {
                    "source": relative_to_root(copied),
                    "alt": f"{title} — view {sequence}",
                }
            )
    except Exception:
        for copied in copied_files:
            copied.unlink(missing_ok=True)
        raise

    item = {
        "id": item_id,
        "title": title,
        "category": category,
        "description": description,
        "price": price,
        "currency": "USD",
        "dimensions": dimensions,
        "materials": materials,
        "year": year,
        "availability": availability,
        "featured": featured,
        "media": media_records,
    }
    catalog["items"].append(item)
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    subprocess.run(["python3", str(ROOT / "build.py")], check=True, cwd=ROOT)
    print(f"\nAdded {title} and mobile-{item_id}.html. Review the site, then commit the new and changed files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
