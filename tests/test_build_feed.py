from __future__ import annotations

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_feed.py"


def load_build_feed():
    spec = importlib.util.spec_from_file_location("build_feed", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildFeedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_build_feed()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.module.ROOT = self.root
        self.module.PODCAST_FILE = self.root / "podcast.yml"
        self.module.SEASONS_DIR = self.root / "seasons"
        self.module.OUTPUT_FILE = self.root / "feed.xml"
        self.write_podcast()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_podcast(self) -> None:
        self.module.PODCAST_FILE.write_text(
            """title: "Катриди заправил"
description: "В этом подкасте мои рассказы звучат голосами разных людей."
language: "ru"
author: "Алексей Катриди"
site_url: "https://katridi.github.io/katridi-zapravil/"
feed_url: "https://katridi.github.io/katridi-zapravil/feed.xml"
artwork:
  url: null
owner:
  name: "Алексей Катриди"
  email: null
itunes:
  category: "Fiction"
  explicit: false
distribution:
  telegram: "https://t.me/katridi_writes"
  empty: null
""",
            encoding="utf-8",
        )

    def write_episode(
        self,
        season: int,
        episode: int,
        guid: str,
        *,
        status: str = "published",
        published_at: str = "2026-09-20T09:00:00+03:00",
        audio_url: str | None = None,
        audio_length: int | None = 12345,
        show_notes: str = "",
    ) -> None:
        if published_at is None:
            published_at_yaml = "null"
        else:
            published_at_yaml = f'"{published_at}"'

        if audio_url is None and status == "draft":
            audio_url_yaml = "null"
        elif audio_url is None:
            audio_url_yaml = f'"https://audio.example.com/s{season:02d}/e{episode:02d}.mp3"'
        else:
            audio_url_yaml = f'"{audio_url}"'

        audio_length_yaml = audio_length if audio_length is not None else "null"

        episode_dir = (
            self.module.SEASONS_DIR
            / f"season-{season:02d}"
            / f"episode-{episode:02d}"
        )
        episode_dir.mkdir(parents=True)
        (episode_dir / "episode.yml").write_text(
            f"""title: "Щенок"
season: {season}
episode: {episode}
episode_type: "full"
author: "Алексей Катриди"
reader: "Сергей Глебкин"
guid: "{guid}"
status: "{status}"
published_at: {published_at_yaml}
audio:
  url: {audio_url_yaml}
  type: "audio/mpeg"
  duration: "00:10:00"
  length: {audio_length_yaml}
description: "Рассказ Алексея Катриди."
{show_notes}
""",
            encoding="utf-8",
        )

    def test_draft_only_feed_has_no_items(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            status="draft",
            published_at=None,
            audio_url=None,
            audio_length=None,
        )

        episode_count, warnings = self.module.write_feed(self.module.OUTPUT_FILE)
        tree = ET.parse(self.module.OUTPUT_FILE)

        self.assertEqual(episode_count, 0)
        self.assertEqual(tree.getroot().findall("./channel/item"), [])
        self.assertTrue(any("artwork.url" in warning for warning in warnings))
        self.assertTrue(any("owner.email" in warning for warning in warnings))

    def test_published_episode_generates_expected_rss(self) -> None:
        self.write_episode(1, 1, "kz-s01e01")

        podcast = self.module.load_podcast_config()
        episodes = self.module.load_published_episodes(podcast)
        tree = self.module.build_feed(podcast, episodes)
        xml = ET.tostring(tree.getroot(), encoding="unicode")

        self.assertEqual(len(episodes), 1)
        self.assertIn("<itunes:explicit>false</itunes:explicit>", xml)
        self.assertIn("<guid isPermaLink=\"false\">kz-s01e01</guid>", xml)
        self.assertIn("<itunes:season>1</itunes:season>", xml)
        self.assertIn("<itunes:episode>1</itunes:episode>", xml)
        self.assertIn("<pubDate>Sun, 20 Sep 2026 09:00:00 +0300</pubDate>", xml)
        self.assertIn('<enclosure url="https://audio.example.com/s01/e01.mp3"', xml)
        self.assertIn('length="12345"', xml)
        self.assertNotIn("<itunes:image", xml)
        self.assertNotIn("<itunes:owner", xml)

    def test_populated_artwork_metadata_generates_rss_image_tags(self) -> None:
        artwork_url = "https://katridi.github.io/katridi-zapravil/assets/cover.jpg"
        self.module.PODCAST_FILE.write_text(
            self.module.PODCAST_FILE.read_text(encoding="utf-8").replace(
                "  url: null",
                f'  url: "{artwork_url}"',
            ),
            encoding="utf-8",
        )

        podcast = self.module.load_podcast_config()
        tree = self.module.build_feed(podcast, [])
        root = tree.getroot()
        xml = ET.tostring(root, encoding="unicode")
        channel = root.find("channel")
        self.assertIsNotNone(channel)

        itunes_images = root.findall(
            "./channel/{http://www.itunes.com/dtds/podcast-1.0.dtd}image"
        )
        self.assertEqual(len(itunes_images), 1)
        self.assertEqual(itunes_images[0].get("href"), artwork_url)

        rss_images = root.findall("./channel/image")
        self.assertEqual(len(rss_images), 1)
        self.assertEqual(rss_images[0].findtext("url"), artwork_url)

        self.assertNotIn('href=""', xml)
        self.assertNotIn("<url />", xml)

    def test_published_episode_uses_head_when_audio_length_is_missing(self) -> None:
        self.write_episode(1, 1, "kz-s01e01", audio_length=None)

        with patch.object(self.module, "get_remote_content_length", return_value=67890):
            podcast = self.module.load_podcast_config()
            episodes = self.module.load_published_episodes(podcast)

        self.assertEqual(episodes[0]["audio_length"], 67890)

    def test_duplicate_guid_is_rejected(self) -> None:
        self.write_episode(1, 1, "kz-s01e01")
        self.write_episode(1, 2, "kz-s01e01")

        podcast = self.module.load_podcast_config()
        with self.assertRaisesRegex(self.module.FeedError, "duplicate GUID"):
            self.module.load_published_episodes(podcast)

    def test_duplicate_season_episode_is_rejected(self) -> None:
        self.write_episode(1, 1, "kz-s01e01")
        duplicate_dir = self.module.SEASONS_DIR / "season-01" / "episode-99"
        duplicate_dir.mkdir(parents=True)
        (duplicate_dir / "episode.yml").write_text(
            (self.module.SEASONS_DIR / "season-01" / "episode-01" / "episode.yml")
            .read_text(encoding="utf-8")
            .replace('guid: "kz-s01e01"', 'guid: "kz-s01e99"'),
            encoding="utf-8",
        )

        podcast = self.module.load_podcast_config()
        with self.assertRaisesRegex(self.module.FeedError, "duplicate season/episode"):
            self.module.load_published_episodes(podcast)

    def test_malformed_publication_date_is_rejected(self) -> None:
        self.write_episode(1, 1, "kz-s01e01", published_at="2026-09-20T09:00:00")

        podcast = self.module.load_podcast_config()
        with self.assertRaisesRegex(self.module.FeedError, "timezone offset"):
            self.module.load_published_episodes(podcast)

    def test_draft_missing_audio_does_not_fail(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            status="draft",
            published_at=None,
            audio_url=None,
            audio_length=None,
        )

        podcast = self.module.load_podcast_config()
        self.assertEqual(self.module.load_published_episodes(podcast), [])

    def test_published_missing_audio_fails(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            audio_url="",
            audio_length=None,
        )

        podcast = self.module.load_podcast_config()
        with self.assertRaisesRegex(self.module.FeedError, "audio.url"):
            self.module.load_published_episodes(podcast)

    def test_http_audio_url_is_rejected(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            audio_url="http://audio.example.com/s01/e01.mp3",
        )

        podcast = self.module.load_podcast_config()
        with self.assertRaisesRegex(self.module.FeedError, "absolute HTTPS URL"):
            self.module.load_published_episodes(podcast)

    def test_show_notes_missing_omits_content_encoded(self) -> None:
        self.write_episode(1, 1, "kz-s01e01")

        podcast = self.module.load_podcast_config()
        episodes = self.module.load_published_episodes(podcast)
        xml = ET.tostring(self.module.build_feed(podcast, episodes).getroot(), encoding="unicode")

        self.assertNotIn("content:encoded", xml)

    def test_show_notes_disabled_omits_content_encoded(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: false
""",
        )

        podcast = self.module.load_podcast_config()
        episodes = self.module.load_published_episodes(podcast)
        xml = ET.tostring(self.module.build_feed(podcast, episodes).getroot(), encoding="unicode")

        self.assertNotIn("content:encoded", xml)

    def test_show_notes_include_description_renders_escaped_paragraph(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: true
  blocks: []
""",
        )

        podcast = self.module.load_podcast_config()
        episode = self.module.load_published_episodes(podcast)[0]

        self.assertEqual(episode["show_notes_html"], "<p>Рассказ Алексея Катриди.</p>")

    def test_paragraph_block_is_escaped(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: false
  blocks:
    - type: paragraph
      text: "<b>Текст</b>"
""",
        )

        podcast = self.module.load_podcast_config()
        episode = self.module.load_published_episodes(podcast)[0]

        self.assertEqual(episode["show_notes_html"], "<p>&lt;b&gt;Текст&lt;/b&gt;</p>")

    def test_telegram_ref_resolves_to_distribution_url(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: false
  blocks:
    - type: link
      ref: telegram
      label: "Telegram «Катриди заправил»"
""",
        )

        podcast = self.module.load_podcast_config()
        episode = self.module.load_published_episodes(podcast)[0]

        self.assertEqual(
            episode["show_notes_html"],
            '<p><a href="https://t.me/katridi_writes">Telegram «Катриди заправил»</a></p>',
        )

    def test_explicit_https_link_renders(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: false
  blocks:
    - type: link
      label: "Текстовая версия рассказа"
      url: "https://example.com/story"
""",
        )

        podcast = self.module.load_podcast_config()
        episode = self.module.load_published_episodes(podcast)[0]

        self.assertEqual(
            episode["show_notes_html"],
            '<p><a href="https://example.com/story">Текстовая версия рассказа</a></p>',
        )

    def test_unknown_ref_fails_validation(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  blocks:
    - type: link
      ref: missing
      label: "Missing"
""",
        )

        with self.assertRaisesRegex(self.module.FeedError, "unknown show_notes link ref"):
            self.module.load_published_episodes(self.module.load_podcast_config())

    def test_null_distribution_ref_fails_validation(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  blocks:
    - type: link
      ref: empty
      label: "Empty"
""",
        )

        with self.assertRaisesRegex(self.module.FeedError, "null or empty"):
            self.module.load_published_episodes(self.module.load_podcast_config())

    def test_link_without_label_fails_validation(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  blocks:
    - type: link
      url: "https://example.com/story"
""",
        )

        with self.assertRaisesRegex(self.module.FeedError, "label is required"):
            self.module.load_published_episodes(self.module.load_podcast_config())

    def test_link_with_ref_and_url_fails_validation(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  blocks:
    - type: link
      ref: telegram
      url: "https://example.com/story"
      label: "Both"
""",
        )

        with self.assertRaisesRegex(self.module.FeedError, "exactly one of ref or url"):
            self.module.load_published_episodes(self.module.load_podcast_config())

    def test_raw_text_special_characters_are_escaped(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  blocks:
    - type: paragraph
      text: '< > & "'
""",
        )

        podcast = self.module.load_podcast_config()
        episode = self.module.load_published_episodes(podcast)[0]

        self.assertEqual(episode["show_notes_html"], "<p>&lt; &gt; &amp; &quot;</p>")

    def test_rss_description_stays_plain_text_with_content_encoded(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: false
  blocks:
    - type: paragraph
      text: "<b>notes</b>"
""",
        )

        podcast = self.module.load_podcast_config()
        episodes = self.module.load_published_episodes(podcast)
        xml = ET.tostring(self.module.build_feed(podcast, episodes).getroot(), encoding="unicode")

        self.assertIn("<description>Рассказ Алексея Катриди.</description>", xml)
        self.assertNotIn("<description><p>", xml)
        self.assertIn("<content:encoded><![CDATA[<p>&lt;b&gt;notes&lt;/b&gt;</p>]]></content:encoded>", xml)

    def test_preview_uses_same_renderer_output_as_rss_episode(self) -> None:
        self.write_episode(
            1,
            1,
            "kz-s01e01",
            show_notes="""show_notes:
  enabled: true
  include_description: true
  blocks:
    - type: link
      ref: telegram
      label: "Telegram «Катриди заправил»"
""",
        )

        podcast = self.module.load_podcast_config()
        source = self.module.SEASONS_DIR / "season-01" / "episode-01" / "episode.yml"
        raw_episode = self.module.load_yaml(source)
        rss_episode = self.module.load_published_episodes(podcast)[0]
        preview_html = self.module.render_show_notes_html(raw_episode, podcast, source)

        self.assertEqual(preview_html, rss_episode["show_notes_html"])


if __name__ == "__main__":
    unittest.main()
