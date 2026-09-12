from __future__ import annotations

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


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
""",
            encoding="utf-8",
        )

    def write_episode(
        self,
        season: int,
        episode: int,
        guid: str,
        *,
        published_at: str = "2026-09-20T09:00:00+03:00",
    ) -> None:
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
status: "published"
published_at: "{published_at}"
audio:
  url: "https://audio.example.com/s{season:02d}/e{episode:02d}.mp3"
  type: "audio/mpeg"
  duration: "00:10:00"
  length: 12345
description: "Рассказ Алексея Катриди."
""",
            encoding="utf-8",
        )

    def test_published_episode_generates_expected_rss(self) -> None:
        self.write_episode(1, 1, "kz-s01e01")

        podcast = self.module.load_podcast_config()
        episodes = self.module.load_published_episodes(podcast)
        tree = self.module.build_feed(podcast, episodes)
        xml = ET.tostring(tree.getroot(), encoding="unicode")

        self.assertEqual(len(episodes), 1)
        self.assertIn("<itunes:explicit>false</itunes:explicit>", xml)
        self.assertIn('<enclosure url="https://audio.example.com/s01/e01.mp3"', xml)
        self.assertIn('length="12345"', xml)
        self.assertNotIn("<itunes:image", xml)
        self.assertNotIn("<itunes:owner", xml)

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


if __name__ == "__main__":
    unittest.main()
