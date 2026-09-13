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
    feed.xml, or another path passed as the first argument
"""

from __future__ import annotations

import email.utils
import html
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


class CDATA(str):
    pass


_original_serialize_xml = ET._serialize_xml


def _serialize_xml_with_cdata(write, elem, qnames, namespaces, short_empty_elements=True, **kwargs):
    if isinstance(elem.text, CDATA):
        text = elem.text
        elem.text = None
        write(f"<{qnames[elem.tag]}>")
        write(f"<![CDATA[{text}]]>")
        for child in elem:
            ET._serialize_xml(write, child, qnames, namespaces, short_empty_elements=short_empty_elements)
        write(f"</{qnames[elem.tag]}>")
        elem.text = text
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
        return
    _original_serialize_xml(write, elem, qnames, namespaces, short_empty_elements=short_empty_elements)


ET._serialize_xml = _serialize_xml_with_cdata


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


def require_named(data: dict[str, Any], key: str, label: str, source: Path) -> Any:
    value = data.get(key)
    if value is None or value == "":
        fail(f"{source}: missing required field '{label}'")
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


def require_optional_mapping(data: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        fail(f"{source}: '{key}' must be an object")
    return value


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
    distribution = require_optional_mapping(data, "distribution", PODCAST_FILE)

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
        "distribution": distribution,
    }


def collect_warnings(podcast: dict[str, Any]) -> list[str]:
    warnings = []

    if not podcast["artwork_url"]:
        warnings.append(
            "WARNING: podcast.yml artwork.url is empty. "
            "Set a public JPG/PNG artwork URL before submitting the feed."
        )

    if not podcast["owner_email"]:
        warnings.append(
            "WARNING: podcast.yml owner.email is empty. "
            "Set an email before platform ownership verification."
        )

    return warnings


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


def render_show_notes_html(
    episode: dict[str, Any],
    podcast: dict[str, Any],
    source: Path,
) -> str | None:
    show_notes = episode.get("show_notes")
    if show_notes is None:
        return None
    if not isinstance(show_notes, dict):
        fail(f"{source}: show_notes must be an object")

    enabled = show_notes.get("enabled", False)
    if not isinstance(enabled, bool):
        fail(f"{source}: show_notes.enabled must be a YAML boolean")
    if not enabled:
        return None

    include_description = show_notes.get("include_description", False)
    if not isinstance(include_description, bool):
        fail(f"{source}: show_notes.include_description must be a YAML boolean")

    blocks = show_notes.get("blocks", [])
    if blocks is None:
        blocks = []
    if not isinstance(blocks, list):
        fail(f"{source}: show_notes.blocks must be a list")

    html_parts: list[str] = []
    description = str(episode.get("description", "")).strip()
    if include_description and description:
        html_parts.append(f"<p>{html.escape(description)}</p>")

    distribution = podcast.get("distribution", {})
    if not isinstance(distribution, dict):
        distribution = {}

    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            fail(f"{source}: show_notes.blocks[{index}] must be an object")

        block_type = block.get("type")
        if block_type == "paragraph":
            text = block.get("text")
            if text is None:
                fail(f"{source}: show_notes.blocks[{index}].text is required")
            html_parts.append(f"<p>{html.escape(str(text).strip())}</p>")
            continue

        if block_type == "link":
            label = block.get("label")
            if label is None or str(label).strip() == "":
                fail(f"{source}: show_notes.blocks[{index}].label is required")

            has_ref = "ref" in block
            has_url = "url" in block
            if has_ref == has_url:
                fail(f"{source}: show_notes.blocks[{index}] must have exactly one of ref or url")

            if has_ref:
                ref = block.get("ref")
                if ref is None or str(ref).strip() == "":
                    fail(f"{source}: show_notes.blocks[{index}].ref must be non-empty")
                ref_key = str(ref).strip()
                if ref_key not in distribution:
                    fail(f"{source}: unknown show_notes link ref '{ref_key}'")
                url = distribution.get(ref_key)
                if url is None or str(url).strip() == "":
                    fail(f"{source}: show_notes link ref '{ref_key}' is null or empty")
                url = str(url).strip()
            else:
                url = str(block.get("url")).strip()
                if not url.startswith("https://"):
                    fail(f"{source}: show_notes.blocks[{index}].url must be an absolute HTTPS URL")

            html_parts.append(
                f'<p><a href="{html.escape(url, quote=True)}">{html.escape(str(label).strip())}</a></p>'
            )
            continue

        fail(f"{source}: unsupported show_notes block type '{block_type}'")

    return "\n".join(html_parts)


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

    episode_type = str(require(data, "episode_type", source)).strip().lower()
    if episode_type not in {"full", "trailer", "bonus"}:
        fail(f"{source}: episode_type must be full, trailer, or bonus")

    published_at = parse_datetime(
        str(require(data, "published_at", source)),
        source,
    )

    audio = require(data, "audio", source)
    if not isinstance(audio, dict):
        fail(f"{source}: audio must be an object")

    audio_url = str(require_named(audio, "url", "audio.url", source)).strip()
    audio_type = str(require_named(audio, "type", "audio.type", source)).strip()

    if not audio_url.startswith("https://"):
        fail(f"{source}: audio.url must be an absolute HTTPS URL")

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

    episode_data = {
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
        "show_notes": data.get("show_notes"),
    }
    episode_data["show_notes_html"] = render_show_notes_html(episode_data, podcast, source)
    return episode_data


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

        if episode.get("show_notes_html"):
            content = ET.SubElement(item, f"{{{NS_CONTENT}}}encoded")
            content.text = CDATA(episode["show_notes_html"])

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


def write_feed(output_file: Path = OUTPUT_FILE) -> tuple[int, list[str]]:
    podcast = load_podcast_config()
    episodes = load_published_episodes(podcast)
    tree = build_feed(podcast, episodes)
    indent_xml(tree)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    )

    return len(episodes), collect_warnings(podcast)


def main() -> int:
    try:
        output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_FILE
        episode_count, warnings = write_feed(output_file)

        print(f"Generated {output_file}")
        print(f"Published episodes: {episode_count}")

        for warning in warnings:
            print(warning)

        return 0

    except FeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
