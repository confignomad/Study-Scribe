"""Unit tests for Phase 9 translation plumbing. Offline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services import captions, markdown_export as md
from app.services.captions import CaptionResult
from app.services.playlist import PlaylistEntry


class DetectOriginalLanguageTests(unittest.TestCase):
    def test_uses_info_language(self) -> None:
        self.assertEqual(captions.detect_original_language({"language": "es"}), "es")

    def test_falls_back_to_manual_subtitles(self) -> None:
        info = {"subtitles": {"fr": [{"ext": "vtt", "url": "u"}]}}
        self.assertEqual(captions.detect_original_language(info), "fr")

    def test_falls_back_to_automatic_captions(self) -> None:
        info = {"automatic_captions": {"de": [{"ext": "vtt", "url": "u"}]}}
        self.assertEqual(captions.detect_original_language(info), "de")

    def test_none_when_unknown(self) -> None:
        self.assertIsNone(captions.detect_original_language({}))


class BilingualBodyTests(unittest.TestCase):
    def test_combines_two_tracks_with_labels(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="ss_bi_"))
        orig = tmp / "es.vtt"
        trans = tmp / "en.vtt"
        orig.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHola mundo.\n", encoding="utf-8")
        trans.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello world.\n", encoding="utf-8")

        body = md.build_bilingual_body(str(orig), "Spanish", str(trans), "English")
        self.assertIn("## Original — Spanish", body)
        self.assertIn("Hola mundo.", body)
        self.assertIn("## Translated — English", body)
        self.assertIn("Hello world.", body)
        # Original section comes before translated section.
        self.assertLess(body.index("Hola mundo."), body.index("Hello world."))


class BodyOverrideTests(unittest.TestCase):
    def test_markdown_uses_override_verbatim(self) -> None:
        tmp = tempfile.mkdtemp(prefix="ss_ov_")
        entry = PlaylistEntry(position=1, video_id="v", title="T", url="https://x", duration=60)
        result = CaptionResult("v", "ok", kind="auto", language="en", path=None)
        override = "## Original — Spanish\n\nHola.\n\n## Translated — English\n\nHello."
        out = md.write_video_markdown(
            entry, result, tmp, date_str="2026-06-30",
            language_display="Spanish + English (bilingual)", numbered=False,
            body_override=override,
        )
        content = out.read_text(encoding="utf-8-sig")
        self.assertIn("## Original — Spanish", content)
        self.assertIn("**Language:** Spanish + English (bilingual)", content)


if __name__ == "__main__":
    unittest.main()
