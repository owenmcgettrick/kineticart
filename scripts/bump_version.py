#!/usr/bin/env python3
"""Increment the site version and synchronize it with index.html."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
INDEX_FILE = ROOT / "index.html"
VERSION_PATTERN = re.compile(r"(?<=<span data-site-version>)[^<]+(?=</span>)")


def committed_version() -> str | None:
    result = subprocess.run(
        ["git", "show", "HEAD:VERSION"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    current = VERSION_FILE.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"(\d+)\.(\d+)", current)
    if not match:
        raise ValueError(f"VERSION must use major.minor digits; found {current!r}")

    previous = committed_version()
    if previous is None:
        version = current
    else:
        previous_match = re.fullmatch(r"(\d+)\.(\d+)", previous)
        if not previous_match:
            raise ValueError(f"Committed VERSION must use major.minor digits; found {previous!r}")
        version = f"{previous_match.group(1)}.{int(previous_match.group(2)) + 1}"
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")

    index = INDEX_FILE.read_text(encoding="utf-8")
    updated_index, replacements = VERSION_PATTERN.subn(version, index, count=1)
    if replacements != 1:
        raise RuntimeError("Could not find the footer version in index.html")
    INDEX_FILE.write_text(updated_index, encoding="utf-8")

    subprocess.run(["git", "add", "VERSION", "index.html"], cwd=ROOT, check=True)
    print(f"Site version: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
