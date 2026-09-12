from __future__ import annotations

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build.py"


def load_build():
    spec = importlib.util.spec_from_file_location("build", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_build()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.dist = self.root / "dist"

        self.module.ROOT = self.root
        self.module.DIST_DIR = self.dist
        self.module.build_feed.ROOT = self.root
        self.module.build_feed.PODCAST_FILE = self.root / "podcast.yml"
        self.module.build_feed.SEASONS_DIR = self.root / "seasons"
        self.module.build_feed.OUTPUT_FILE = self.root / "feed.xml"

        (self.root / "assets").mkdir()
        (self.root / "assets" / "cover-placeholder.svg").write_text(
            "<svg></svg>",
            encoding="utf-8",
        )
        (self.root / "index.html").write_text("<!doctype html>\n<title>Test</title>\n")
        (self.root / "style.css").write_text("body { color: #111; }\n")
        (self.dist / "stale.txt").mkdir(parents=True)

        (self.root / "podcast.yml").write_text(
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
        episode_dir = self.root / "seasons" / "season-01" / "episode-01"
        episode_dir.mkdir(parents=True)
        (episode_dir / "episode.yml").write_text(
            """title: "Щенок"
season: 1
season_title: "Воспоминания"
episode: 1
episode_type: "full"
author: "Алексей Катриди"
reader: "Сергей Глебкин"
guid: "kz-s01e01"
status: "draft"
published_at: null
audio:
  url: null
  type: "audio/mpeg"
  duration: null
  length: null
description: "Рассказ Алексея Катриди."
""",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_creates_clean_dist_artifact(self) -> None:
        episode_count, warnings = self.module.build()

        self.assertEqual(episode_count, 0)
        self.assertTrue((self.dist / "index.html").is_file())
        self.assertTrue((self.dist / "style.css").is_file())
        self.assertTrue((self.dist / "assets" / "cover-placeholder.svg").is_file())
        self.assertTrue((self.dist / "feed.xml").is_file())
        self.assertFalse((self.dist / "stale.txt").exists())
        self.assertFalse((self.dist / "podcast.yml").exists())
        self.assertFalse((self.dist / "seasons").exists())
        self.assertTrue(any("artwork.url" in warning for warning in warnings))
        self.assertTrue(any("owner.email" in warning for warning in warnings))

        tree = ET.parse(self.dist / "feed.xml")
        self.assertEqual(tree.getroot().findall("./channel/item"), [])


if __name__ == "__main__":
    unittest.main()
