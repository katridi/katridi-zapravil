from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PlatformParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_platforms = False
        self.platform_depth = 0
        self.items: list[dict[str, str]] = []
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "").split()

        if tag == "div" and "platforms" in classes:
            self.in_platforms = True
            self.platform_depth = 1
            return

        if not self.in_platforms:
            return

        if tag == "div":
            self.platform_depth += 1

        if tag in {"a", "span"} and (
            "platform-badge" in classes or "telegram-link" in classes
        ):
            self.items.append(
                {
                    "tag": tag,
                    "label": attr.get("aria-label", ""),
                    "href": attr.get("href", ""),
                    "target": attr.get("target", ""),
                    "rel": attr.get("rel", ""),
                }
            )

        if tag == "a":
            self.hrefs.append(attr.get("href", ""))

    def handle_endtag(self, tag: str) -> None:
        if self.in_platforms and tag == "div":
            self.platform_depth -= 1
            if self.platform_depth == 0:
                self.in_platforms = False


class StaticSiteTest(unittest.TestCase):
    def test_source_index_uses_platform_placeholder(self) -> None:
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("{{PLATFORMS}}", html)
        self.assertNotIn("https://t.me/katridi_writes", html)
        self.assertNotIn("https://open.spotify.com", html)
        self.assertNotIn("https://podcasts.apple.com", html)

    def test_only_telegram_asset_path_is_referenced(self) -> None:
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        for path in [
            "assets/icons/yandex-music.png",
            "assets/icons/spotify.png",
            "assets/icons/apple-podcasts.png",
            "assets/icons/youtube.png",
        ]:
            self.assertNotIn(path, html)

    def test_source_index_uses_episode_placeholder(self) -> None:
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("{{EPISODES}}", html)
        self.assertIn("{{PLATFORMS}}", html)
        self.assertNotIn("S01E01", html)
        self.assertNotIn("Щенок", html)
        self.assertNotIn("Сергей Глебкин", html)
        self.assertNotIn("Скоро", html)


if __name__ == "__main__":
    unittest.main()
