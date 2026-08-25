#!/usr/bin/env python3
"""Generate web-sized derivatives while retaining every original file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from media_tools import IMAGE_EXTENSIONS, ROOT, VIDEO_EXTENSIONS, optimize_image, optimize_video


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Regenerate existing derivatives")
    parser.add_argument("--images-only", action="store_true", help="Skip video conversion")
    args = parser.parse_args()

    catalog = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    image_count = 0
    video_count = 0

    for item in catalog["items"]:
        print(f"Processing {item['title']}…")
        for media in item["media"]:
            source = ROOT / media["source"]
            extension = source.suffix.lower()
            try:
                if extension in IMAGE_EXTENSIONS:
                    optimize_image(source, item["id"], force=args.force)
                    image_count += 1
                elif extension in VIDEO_EXTENSIONS and not args.images_only:
                    converted = optimize_video(source, item["id"], force=args.force)
                    if converted is None:
                        failures.append(f"Could not convert video: {media['source']}")
                    else:
                        video_count += 1
            except Exception as error:  # report all media problems in one run
                failures.append(f"{media['source']}: {error}")

    print(f"Generated derivatives for {image_count} images and {video_count} videos.")
    if failures:
        print("\nWarnings:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
