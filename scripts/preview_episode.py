#!/usr/bin/env python3
"""
Generate a local browser preview for one episode's RSS show notes HTML.

Run:
    python3 scripts/preview_episode.py seasons/season-01/episode-01/episode.yml
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_feed


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / ".preview"


def make_preview_html(
    episode: dict[str, Any],
    show_notes_html: str | None,
) -> str:
    title = html.escape(str(episode.get("title", "")).strip())
    description = html.escape(str(episode.get("description", "")).strip())
    rendered_show_notes = show_notes_html or ""

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} - show notes preview</title>
  <style>
    body {{
      margin: 0;
      color: #1f1f1f;
      background: #f7f3ec;
      font: 18px/1.6 Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .note {{
      margin: 0 0 28px;
      color: #5f5a52;
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    h1 {{
      margin: 0 0 28px;
      font-size: 32px;
      line-height: 1.15;
    }}
    h2 {{
      margin: 30px 0 10px;
      font: 700 14px/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    a {{
      color: #7a2f1f;
    }}
  </style>
</head>
<body>
  <main>
    <p class="note">Это канонический HTML show notes из RSS. Конкретное оформление может отличаться в разных приложениях.</p>
    <h1>{title}</h1>
    <h2>Описание</h2>
    <p>{description}</p>
    <h2>Show notes</h2>
    {rendered_show_notes}
  </main>
</body>
</html>
"""


def preview_episode(source: Path) -> Path:
    episode_path = source if source.is_absolute() else ROOT / source
    episode = build_feed.load_yaml(episode_path)
    podcast = build_feed.load_podcast_config()
    show_notes_html = build_feed.render_show_notes_html(episode, podcast, episode_path)

    season = int(build_feed.require(episode, "season", episode_path))
    episode_number = int(build_feed.require(episode, "episode", episode_path))

    PREVIEW_DIR.mkdir(exist_ok=True)
    output_path = PREVIEW_DIR / f"s{season:02d}e{episode_number:02d}-show-notes.html"
    output_path.write_text(
        make_preview_html(episode, show_notes_html),
        encoding="utf-8",
    )
    return output_path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/preview_episode.py seasons/season-01/episode-01/episode.yml", file=sys.stderr)
        return 2

    try:
        output_path = preview_episode(Path(sys.argv[1]))
    except build_feed.FeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (TypeError, ValueError) as exc:
        print(f"ERROR: invalid season or episode number: {exc}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
