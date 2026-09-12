#!/usr/bin/env python3
"""
Generate podcast RSS feed from episode YAML files.

Expected episode structure:
    seasons/
      season-01/
        episode-01/
          episode.yml

Only episodes with:
    status: "published"
are included in the RSS feed.

Dependency:
    pip install pyyaml

Run:
    python3 scripts/build_feed.py

Output:
    feed.xml
"""

from __future__ import annotations

import email.utils
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parent
if ROOT.name == "scripts":
    ROOT = ROOT.parent
PODCAST_FILE = ROOT / "podcast.yml"
SEASONS_DIR = ROOT / "seasons"
OUTPUT_FILE = ROOT / "feed.xml"


# ---------------------------------------------------------------------------
# XML namespaces
# ---------------------------------------------------------------------------

NS_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"

ET.register_namespace("itunes", NS_ITUNES)
ET.register_namespace("atom", NS_ATOM)
ET.register_namespace("content", NS_CONTENT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FeedError(Exception):
    pass


def fail(message: str) -> None:
    raise FeedError(message)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path}: cannot read YAML: {exc}")

    if not isinstance(data, dict):
        fail(f"{path}: YAML root must be a mapping/object")

    return data


def require(data: dict[str, Any], key: str, source: Path) -> Any:
    value = data.get(key)
    if value is None or value == "":
        fail(f"{source}: missing required field '{key}'")
    return value


def require_mapping(data: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    value = require(data, key, source)
    if not isinstance(value, dict):
        fail(f"{source}: '{key}' must be an object")
    return value


def rss_bool(value: Any, source: Path, key: str) -> str:
    if not isinstance(value, bool):
        fail(f"{source}: {key} must be a YAML boolean")
    return "true" if value else "false"


def optional_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    return str(value).strip()


def load_podcast_config() -> dict[str, Any]:
    data = load_yaml(PODCAST_FILE)

    artwork = data.get("artwork")
    if artwork is None:
        artwork = {}
    if not isinstance(artwork, dict):
        fail(f"{PODCAST_FILE}: 'artwork' must be an object")

    owner = data.get("owner")
    if owner is None:
        owner = {}
    if not isinstance(owner, dict):
        fail(f"{PODCAST_FILE}: 'owner' must be an object")

    itunes = require_mapping(data, "itunes", PODCAST_FILE)

    return {
        "title": str(require(data, "title", PODCAST_FILE)).strip(),
        "description": str(require(data, "description", PODCAST_FILE)).strip(),
        "language": str(require(data, "language", PODCAST_FILE)).strip(),
        "author": str(require(data, "author", PODCAST_FILE)).strip(),
        "site_url": str(require(data, "site_url", PODCAST_FILE)).strip(),
        "feed_url": str(require(data, "feed_url", PODCAST_FILE)).strip(),
        "artwork_url": optional_text(artwork, "url"),
        "owner_name": optional_text(owner, "name"),
        "owner_email": optional_text(owner, "email"),
        "itunes_category": str(require(itunes, "category", PODCAST_FILE)).strip(),
        "itunes_explicit": rss_bool(
            require(itunes, "explicit", PODCAST_FILE),
            PODCAST_FILE,
            "itunes.explicit",
        ),
    }


def parse_datetime(value: str, source: Path) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        fail(
            f"{source}: published_at must be ISO 8601, "
            f"for example 2026-09-20T09:00:00+03:00"
        )

    if dt.tzinfo is None:
        fail(f"{source}: published_at must include a timezone offset")

    return dt


def rfc2822(dt: datetime) -> str:
    return email.utils.format_datetime(dt)


def add_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    element = ET.SubElement(parent, tag)
    element.text = str(value)
    return element


def get_remote_content_length(url: str) -> int:
    """
    Get Content-Length from the public audio URL.

    Podcast RSS enclosure length is the file size in bytes.

    HEAD is attempted first because podcast audio hosting should support it.
    """
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "katridi-zapravil-feed-builder/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = response.headers.get("Content-Length")
    except Exception as exc:
        fail(f"Cannot HEAD audio URL {url}: {exc}")

    if not value:
        fail(f"Audio URL does not return Content-Length: {url}")

    try:
        return int(value)
    except ValueError:
        fail(f"Invalid Content-Length returned by {url}: {value}")


def validate_episode(
    data: dict[str, Any],
    source: Path,
    podcast: dict[str, Any],
    seen_guids: set[str],
    seen_numbers: set[tuple[int, int]],
) -> dict[str, Any]:
    title = str(require(data, "title", source)).strip()

    try:
        season = int(require(data, "season", source))
        episode = int(require(data, "episode", source))
    except (TypeError, ValueError):
        fail(f"{source}: season and episode must be integers")

    if season < 1 or episode < 1:
        fail(f"{source}: season and episode must be positive integers")

    guid = str(require(data, "guid", source)).strip()

    if guid in seen_guids:
        fail(f"{source}: duplicate GUID '{guid}'")
    seen_guids.add(guid)

    number_key = (season, episode)
    if number_key in seen_numbers:
        fail(f"{source}: duplicate season/episode S{season:02d}E{episode:02d}")
    seen_numbers.add(number_key)

    episode_type = str(data.get("episode_type", "full")).strip().lower()
    if episode_type not in {"full", "trailer", "bonus"}:
        fail(f"{source}: episode_type must be full, trailer, or bonus")

    published_at = parse_datetime(
        str(require(data, "published_at", source)),
        source,
    )

    audio = require(data, "audio", source)
    if not isinstance(audio, dict):
        fail(f"{source}: audio must be an object")

    audio_url = str(require(audio, "url", source)).strip()
    audio_type = str(require(audio, "type", source)).strip()

    if not audio_url.startswith(("https://", "http://")):
        fail(f"{source}: audio.url must be an absolute HTTP(S) URL")

    description = str(data.get("description", "")).strip()
    author = str(data.get("author", podcast["author"])).strip()
    reader = str(data.get("reader", "")).strip()
    duration = audio.get("duration")

    length = audio.get("length")
    if length is None:
        length = get_remote_content_length(audio_url)

    try:
        length = int(length)
    except (TypeError, ValueError):
        fail(f"{source}: audio.length must be an integer number of bytes")

    return {
        "title": title,
        "season": season,
        "episode": episode,
        "episode_type": episode_type,
        "author": author,
        "reader": reader,
        "guid": guid,
        "published_at": published_at,
        "audio_url": audio_url,
        "audio_type": audio_type,
        "audio_length": length,
        "duration": duration,
        "description": description,
    }


def load_published_episodes(podcast: dict[str, Any]) -> list[dict[str, Any]]:
    if not SEASONS_DIR.exists():
        return []

    episode_files = sorted(SEASONS_DIR.glob("season-*/episode-*/episode.yml"))

    episodes: list[dict[str, Any]] = []
    seen_guids: set[str] = set()
    seen_numbers: set[tuple[int, int]] = set()

    for source in episode_files:
        data = load_yaml(source)

        status = str(data.get("status", "draft")).strip().lower()

        if status == "draft":
            continue

        if status != "published":
            fail(
                f"{source}: status must be either 'draft' or 'published', "
                f"got '{status}'"
            )

        episode = validate_episode(data, source, podcast, seen_guids, seen_numbers)
        episodes.append(episode)

    # Newest first, as podcast RSS feeds normally are.
    episodes.sort(key=lambda item: item["published_at"], reverse=True)

    return episodes


# ---------------------------------------------------------------------------
# RSS generation
# ---------------------------------------------------------------------------

def build_feed(podcast: dict[str, Any], episodes: list[dict[str, Any]]) -> ET.ElementTree:
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = ET.SubElement(rss, "channel")

    add_text(channel, "title", podcast["title"])
    add_text(channel, "link", podcast["site_url"])
    add_text(channel, "description", podcast["description"])
    add_text(channel, "language", podcast["language"])

    add_text(channel, f"{{{NS_ITUNES}}}author", podcast["author"])
    add_text(channel, f"{{{NS_ITUNES}}}explicit", podcast["itunes_explicit"])

    ET.SubElement(
        channel,
        f"{{{NS_ITUNES}}}category",
        {"text": podcast["itunes_category"]},
    )

    # Atom self-link helps podcast clients identify the canonical feed URL.
    ET.SubElement(
        channel,
        f"{{{NS_ATOM}}}link",
        {
            "href": podcast["feed_url"],
            "rel": "self",
            "type": "application/rss+xml",
        },
    )

    if podcast["artwork_url"]:
        ET.SubElement(
            channel,
            f"{{{NS_ITUNES}}}image",
            {"href": podcast["artwork_url"]},
        )

        image = ET.SubElement(channel, "image")
        add_text(image, "url", podcast["artwork_url"])
        add_text(image, "title", podcast["title"])
        add_text(image, "link", podcast["site_url"])

    if podcast["owner_email"]:
        owner = ET.SubElement(channel, f"{{{NS_ITUNES}}}owner")
        add_text(owner, f"{{{NS_ITUNES}}}name", podcast["owner_name"] or podcast["author"])
        add_text(owner, f"{{{NS_ITUNES}}}email", podcast["owner_email"])

    for episode in episodes:
        item = ET.SubElement(channel, "item")

        add_text(item, "title", episode["title"])

        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = episode["guid"]

        add_text(item, "pubDate", rfc2822(episode["published_at"]))

        description = episode["description"]
        if description:
            add_text(item, "description", description)

        ET.SubElement(
            item,
            "enclosure",
            {
                "url": episode["audio_url"],
                "length": str(episode["audio_length"]),
                "type": episode["audio_type"],
            },
        )

        add_text(item, f"{{{NS_ITUNES}}}author", episode["author"])
        add_text(item, f"{{{NS_ITUNES}}}season", episode["season"])
        add_text(item, f"{{{NS_ITUNES}}}episode", episode["episode"])
        add_text(item, f"{{{NS_ITUNES}}}episodeType", episode["episode_type"])
        add_text(item, f"{{{NS_ITUNES}}}explicit", podcast["itunes_explicit"])

        if episode["duration"]:
            add_text(
                item,
                f"{{{NS_ITUNES}}}duration",
                episode["duration"],
            )

    return ET.ElementTree(rss)


def indent_xml(tree: ET.ElementTree) -> None:
    # Python 3.9+
    ET.indent(tree, space="  ")


def main() -> int:
    try:
        podcast = load_podcast_config()
        episodes = load_published_episodes(podcast)
        tree = build_feed(podcast, episodes)
        indent_xml(tree)

        tree.write(
            OUTPUT_FILE,
            encoding="utf-8",
            xml_declaration=True,
            short_empty_elements=True,
        )

        print(f"Generated {OUTPUT_FILE}")
        print(f"Published episodes: {len(episodes)}")

        if not podcast["artwork_url"]:
            print(
                "WARNING: podcast.yml artwork.url is empty. "
                "Set a public JPG/PNG artwork URL before submitting the feed."
            )

        if not podcast["owner_email"]:
            print(
                "WARNING: podcast.yml owner.email is empty. "
                "Set an email before platform ownership verification."
            )

        return 0

    except FeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
