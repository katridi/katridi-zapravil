#!/usr/bin/env python3
"""
Build the public GitHub Pages artifact in dist/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_feed


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
STATIC_FILES = ("index.html", "style.css")
STATIC_DIRS = ("assets",)


class BuildError(Exception):
    pass


def clean_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()


def copy_static_site() -> None:
    for name in STATIC_FILES:
        source = ROOT / name
        if not source.is_file():
            raise BuildError(f"Missing required static file: {source}")
        shutil.copy2(source, DIST_DIR / name)

    for name in STATIC_DIRS:
        source = ROOT / name
        if not source.exists():
            continue
        if not source.is_dir():
            raise BuildError(f"Expected static asset directory: {source}")
        shutil.copytree(
            source,
            DIST_DIR / name,
            ignore=shutil.ignore_patterns(".*"),
        )


def build() -> tuple[int, list[str]]:
    clean_dist()
    copy_static_site()
    return build_feed.write_feed(DIST_DIR / "feed.xml")


def main() -> int:
    try:
        episode_count, warnings = build()
    except (BuildError, build_feed.FeedError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Built {DIST_DIR}")
    print(f"Published episodes: {episode_count}")
    for warning in warnings:
        print(warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
