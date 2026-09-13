#!/usr/bin/env python3
"""
Build the public GitHub Pages artifact in dist/.
"""

from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_feed


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
STATIC_FILES = ("index.html", "style.css")
STATIC_DIRS = ("assets",)
EPISODES_PLACEHOLDER = "{{EPISODES}}"
PLATFORMS_PLACEHOLDER = "{{PLATFORMS}}"


class BuildError(Exception):
    pass


def clean_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()


def load_homepage_episodes() -> list[dict[str, Any]]:
    if not build_feed.SEASONS_DIR.exists():
        return []

    episodes: list[dict[str, Any]] = []
    seen_numbers: set[tuple[int, int]] = set()

    for source in sorted(build_feed.SEASONS_DIR.glob("season-*/episode-*/episode.yml")):
        data = build_feed.load_yaml(source)

        try:
            season = int(build_feed.require(data, "season", source))
            episode = int(build_feed.require(data, "episode", source))
        except (TypeError, ValueError):
            raise build_feed.FeedError(f"{source}: season and episode must be integers")

        if season < 1 or episode < 1:
            raise build_feed.FeedError(f"{source}: season and episode must be positive integers")

        number_key = (season, episode)
        if number_key in seen_numbers:
            raise build_feed.FeedError(f"{source}: duplicate season/episode S{season:02d}E{episode:02d}")
        seen_numbers.add(number_key)

        status = str(data.get("status", "draft")).strip().lower()
        published_at = data.get("published_at")
        display_date = "Скоро"

        if status == "published":
            if published_at is None or published_at == "":
                raise build_feed.FeedError(f"{source}: missing required field 'published_at'")
            display_date = build_feed.parse_datetime(str(published_at), source).strftime("%d.%m.%Y")
        elif status != "draft":
            raise build_feed.FeedError(
                f"{source}: status must be either 'draft' or 'published', got '{status}'"
            )

        summary = data.get("homepage_summary")
        if summary is None:
            summary = data.get("description", "")

        episodes.append(
            {
                "season": season,
                "episode": episode,
                "title": str(build_feed.require(data, "title", source)).strip(),
                "reader": str(data.get("reader", "")).strip(),
                "summary": str(summary).strip(),
                "status": status,
                "display_date": display_date,
            }
        )

    episodes.sort(key=lambda item: (item["season"], item["episode"]))
    return episodes


def render_homepage_episodes(episodes: list[dict[str, Any]]) -> str:
    rendered = []

    for episode in episodes:
        code = f"S{episode['season']:02d}E{episode['episode']:02d}"
        reader = episode["reader"]
        reader_html = ""
        if reader:
            reader_html = f'\n          <p class="episode-meta">Читает {html.escape(reader)}</p>'

        rendered.append(
            f"""<article class="episode">
        <div>
          <p class="episode-number">{code}</p>
          <h3>{html.escape(episode["title"])}</h3>{reader_html}
        </div>

        <p class="episode-description">
          {html.escape(episode["summary"])}
        </p>

        <span class="status">{html.escape(episode["display_date"])}</span>
      </article>"""
        )

    return "\n\n      ".join(rendered)


def platform_badge(label: str, aria_label: str, url: Any) -> str:
    if url is None or str(url).strip() == "":
        return (
            f'<span class="platform-badge platform-badge-unavailable" '
            f'aria-label="{html.escape(aria_label, quote=True)}">{html.escape(label)}</span>'
        )

    href = html.escape(str(url).strip(), quote=True)
    return (
        f'<a class="platform-badge" href="{href}" '
        f'aria-label="{html.escape(aria_label, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
    )


def render_platforms(podcast: dict[str, Any]) -> str:
    distribution = podcast.get("distribution", {})
    if not isinstance(distribution, dict):
        distribution = {}

    telegram_url = distribution.get("telegram")
    if telegram_url is None or str(telegram_url).strip() == "":
        raise BuildError("podcast.yml distribution.telegram is required for the homepage")

    return f"""<div class="platforms" aria-label="Платформы">
          <div class="platform-grid">
            {platform_badge("Яндекс Музыка", "Яндекс Музыка", distribution.get("yandex_music"))}
            {platform_badge("Spotify", "Spotify", distribution.get("spotify"))}
            {platform_badge("Apple Podcasts", "Apple Podcasts", distribution.get("apple_podcasts"))}
            {platform_badge("YouTube", "YouTube Music", distribution.get("youtube"))}
          </div>
          <a class="telegram-link" href="{html.escape(str(telegram_url).strip(), quote=True)}" aria-label="Telegram" target="_blank" rel="noopener noreferrer">
            <img class="platform-icon-square" src="assets/icons/telegram.png" alt="">
            <span>Читать Катриди заправил</span>
          </a>
        </div>"""


def render_index_html(podcast: dict[str, Any]) -> None:
    source = ROOT / "index.html"
    if not source.is_file():
        raise BuildError(f"Missing required static file: {source}")

    template = source.read_text(encoding="utf-8")
    if EPISODES_PLACEHOLDER not in template:
        raise BuildError(f"Missing {EPISODES_PLACEHOLDER} placeholder in {source}")
    if PLATFORMS_PLACEHOLDER not in template:
        raise BuildError(f"Missing {PLATFORMS_PLACEHOLDER} placeholder in {source}")

    html_output = template.replace(
        EPISODES_PLACEHOLDER,
        render_homepage_episodes(load_homepage_episodes()),
    )
    html_output = html_output.replace(
        PLATFORMS_PLACEHOLDER,
        render_platforms(podcast),
    )
    (DIST_DIR / "index.html").write_text(html_output, encoding="utf-8")


def copy_static_site(podcast: dict[str, Any]) -> None:
    render_index_html(podcast)

    for name in STATIC_FILES:
        if name == "index.html":
            continue
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


def write_feed_from_loaded(
    podcast: dict[str, Any],
    published_episodes: list[dict[str, Any]],
) -> None:
    tree = build_feed.build_feed(podcast, published_episodes)
    build_feed.indent_xml(tree)
    tree.write(
        DIST_DIR / "feed.xml",
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    )


def build() -> tuple[int, list[str]]:
    clean_dist()
    podcast = build_feed.load_podcast_config()
    published_episodes = build_feed.load_published_episodes(podcast)
    copy_static_site(podcast)
    write_feed_from_loaded(podcast, published_episodes)
    return len(published_episodes), build_feed.collect_warnings(podcast)


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
