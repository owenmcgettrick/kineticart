"""Shared media helpers for the static Kinetic Creations site."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "img" / "web"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".webm"}


def slugify(value: str) -> str:
    value = value.strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def media_stem(path: Path) -> str:
    return slugify(path.stem) or "media"


def web_directory(item_id: str) -> Path:
    return WEB_ROOT / item_id


def image_derivative_paths(source: Path, item_id: str) -> list[tuple[int, Path]]:
    stem = media_stem(source)
    folder = web_directory(item_id)
    return [(720, folder / f"{stem}-720.webp"), (1440, folder / f"{stem}-1440.webp")]


def video_derivative_path(source: Path, item_id: str) -> Path:
    return web_directory(item_id) / f"{media_stem(source)}-480.m4v"


def optimize_image(source: Path, item_id: str, *, force: bool = False) -> list[Path]:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    outputs: list[Path] = []
    with Image.open(source) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
        rendered_widths: set[int] = set()
        for target_width, destination in image_derivative_paths(source, item_id):
            output_width = min(image.width, target_width)
            if output_width in rendered_widths:
                # A small original does not need duplicate 720 and 1440 files.
                destination.unlink(missing_ok=True)
                continue
            rendered_widths.add(output_width)
            if destination.exists() and not force:
                outputs.append(destination)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            rendered = image.copy()
            if rendered.width > target_width:
                target_height = round(rendered.height * target_width / rendered.width)
                rendered = rendered.resize((target_width, target_height), Image.Resampling.LANCZOS)
            rendered.save(destination, "WEBP", quality=82, method=6)
            outputs.append(destination)
    return outputs


def optimize_video(source: Path, item_id: str, *, force: bool = False) -> Path | None:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    destination = video_derivative_path(source, item_id)
    if destination.exists() and not force:
        return destination

    converter = shutil.which("avconvert")
    if converter is None:
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        converter,
        "--source",
        str(source),
        "--preset",
        "PresetAppleM4V480pSD",
        "--output",
        str(destination),
        "--replace",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        destination.unlink(missing_ok=True)
        return None
    return destination


def copy_media(source: Path, item_id: str, sequence: int) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    extension = source.suffix.lower()
    if extension not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported media type: {extension}")

    destination_dir = ROOT / "img" / item_id.replace("-", "_")
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{item_id}.{sequence}{extension}"
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copy2(source, destination)
    return destination


def relative_to_root(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()
