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
        (self.root / "assets" / "cover.jpg").write_bytes(b"jpg")
        (self.root / "assets" / "icons").mkdir()
        for icon_name in [
            "yandex-music.png",
            "spotify.png",
            "apple-podcasts.png",
            "youtube.png",
            "telegram.png",
        ]:
            (self.root / "assets" / "icons" / icon_name).write_bytes(b"png")
        (self.root / "assets" / "icons" / ".DS_Store").write_bytes(b"local")
        (self.root / "index.html").write_text(
            "<!doctype html>\n<title>Test</title>\n{{EPISODES}}\n",
            encoding="utf-8",
        )
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
homepage_summary: "Первый рассказ мини-сезона «Воспоминания»"
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
        self.assertTrue((self.dist / "assets" / "cover.jpg").is_file())
        self.assertTrue((self.dist / "assets" / "icons" / "yandex-music.png").is_file())
        self.assertTrue((self.dist / "assets" / "icons" / "spotify.png").is_file())
        self.assertTrue((self.dist / "assets" / "icons" / "apple-podcasts.png").is_file())
        self.assertTrue((self.dist / "assets" / "icons" / "youtube.png").is_file())
        self.assertTrue((self.dist / "assets" / "icons" / "telegram.png").is_file())
        self.assertTrue((self.dist / "feed.xml").is_file())
        self.assertFalse((self.dist / "stale.txt").exists())
        self.assertFalse((self.dist / "assets" / "icons" / ".DS_Store").exists())
        self.assertFalse((self.dist / "podcast.yml").exists())
        self.assertFalse((self.dist / "seasons").exists())
        self.assertTrue(any("artwork.url" in warning for warning in warnings))
        self.assertTrue(any("owner.email" in warning for warning in warnings))

        tree = ET.parse(self.dist / "feed.xml")
        self.assertEqual(tree.getroot().findall("./channel/item"), [])

    def write_episode(
        self,
        season: int,
        episode: int,
        *,
        title: str = "Щенок",
        reader: str = "Сергей Глебкин",
        status: str = "draft",
        published_at: str | None = None,
        description: str = "Рассказ Алексея Катриди.",
        homepage_summary: str | None = "Первый рассказ мини-сезона «Воспоминания»",
    ) -> None:
        def yaml_quote(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"

        episode_dir = self.root / "seasons" / f"season-{season:02d}" / f"episode-{episode:02d}"
        episode_dir.mkdir(parents=True, exist_ok=True)
        published_yaml = "null" if published_at is None else f'"{published_at}"'
        summary_yaml = ""
        if homepage_summary is not None:
            summary_yaml = f"homepage_summary: {yaml_quote(homepage_summary)}\n"

        (episode_dir / "episode.yml").write_text(
            f"""title: {yaml_quote(title)}
season: {season}
season_title: "Воспоминания"
episode: {episode}
episode_type: "full"
author: "Алексей Катриди"
reader: {yaml_quote(reader)}
guid: "kz-s{season:02d}e{episode:02d}"
status: "{status}"
published_at: {published_yaml}
audio:
  url: "https://audio.example.com/s{season:02d}/e{episode:02d}.mp3"
  type: "audio/mpeg"
  duration: "00:04:16"
  length: 12345
description: {yaml_quote(description)}
{summary_yaml}""",
            encoding="utf-8",
        )

    def test_homepage_renders_draft_episode_as_soon(self) -> None:
        self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertIn("S01E01", html)
        self.assertIn("Щенок", html)
        self.assertIn("Сергей Глебкин", html)
        self.assertIn("Первый рассказ мини-сезона «Воспоминания»", html)
        self.assertIn("Скоро", html)

    def test_homepage_renders_published_episode_date(self) -> None:
        self.write_episode(
            1,
            1,
            status="published",
            published_at="2026-09-20T09:00:00+03:00",
        )

        self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertIn("20.09.2026", html)
        self.assertNotIn("09:00:00", html)

    def test_homepage_orders_episodes_by_season_and_episode(self) -> None:
        self.write_episode(1, 1, title="Первый")
        self.write_episode(2, 1, title="Третий")
        self.write_episode(1, 2, title="Второй")

        self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertLess(html.index("S01E01"), html.index("S01E02"))
        self.assertLess(html.index("S01E02"), html.index("S02E01"))

    def test_homepage_escapes_yaml_text(self) -> None:
        self.write_episode(
            1,
            1,
            title='<Щенок & "друг">',
            reader='Сергей <Глебкин> & "читатель"',
            description='Описание < > & "',
            homepage_summary=None,
        )

        self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertIn("&lt;Щенок &amp; &quot;друг&quot;&gt;", html)
        self.assertIn("Сергей &lt;Глебкин&gt; &amp; &quot;читатель&quot;", html)
        self.assertIn("Описание &lt; &gt; &amp; &quot;", html)
        self.assertNotIn('<Щенок & "друг">', html)

    def test_published_episode_without_published_at_fails_build(self) -> None:
        self.write_episode(1, 1, status="published", published_at=None)

        with self.assertRaisesRegex(self.module.build_feed.FeedError, "published_at"):
            self.module.build()

    def test_draft_episode_without_published_at_builds(self) -> None:
        self.write_episode(1, 1, status="draft", published_at=None)

        episode_count, _warnings = self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertEqual(episode_count, 0)
        self.assertIn("Скоро", html)

    def test_dist_index_contains_generated_episode_markup(self) -> None:
        self.module.build()
        html = (self.dist / "index.html").read_text(encoding="utf-8")

        self.assertIn('<article class="episode">', html)
        self.assertNotIn("{{EPISODES}}", html)


if __name__ == "__main__":
    unittest.main()
