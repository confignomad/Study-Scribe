"""Unit tests for app.services.captions (Phase 4).

Offline: exercises the pure track-selection logic against hand-built yt-dlp
info dicts. The networked/filesystem function (fetch_video_captions) is not
called here.

Run from the StudyScribe/ directory:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from app.services import captions


class SelectCaptionTrackTests(unittest.TestCase):
    def test_prefers_manual_over_auto(self) -> None:
        info = {
            "subtitles": {"en": [{"ext": "vtt", "url": "MANUAL"}]},
            "automatic_captions": {"en": [{"ext": "vtt", "url": "AUTO"}]},
        }
        track = captions.select_caption_track(info, "en")
        self.assertEqual(track["kind"], "manual")
        self.assertEqual(track["url"], "MANUAL")

    def test_falls_back_to_auto_when_no_manual(self) -> None:
        info = {
            "subtitles": {},
            "automatic_captions": {"en": [{"ext": "vtt", "url": "AUTO"}]},
        }
        track = captions.select_caption_track(info, "en")
        self.assertEqual(track["kind"], "auto")
        self.assertEqual(track["url"], "AUTO")

    def test_regional_variant_matches_base_language(self) -> None:
        info = {"subtitles": {"en-US": [{"ext": "vtt", "url": "US"}]}}
        track = captions.select_caption_track(info, "en")
        self.assertIsNotNone(track)
        self.assertEqual(track["language"], "en-US")

    def test_prefers_vtt_by_format_priority(self) -> None:
        info = {
            "subtitles": {
                "en": [
                    {"ext": "json3", "url": "JSON"},
                    {"ext": "vtt", "url": "VTT"},
                ]
            }
        }
        track = captions.select_caption_track(info, "en")
        self.assertEqual(track["ext"], "vtt")
        self.assertEqual(track["url"], "VTT")

    def test_no_captions_for_requested_language(self) -> None:
        info = {"subtitles": {"es": [{"ext": "vtt", "url": "ES"}]}, "automatic_captions": {}}
        self.assertIsNone(captions.select_caption_track(info, "de"))

    def test_empty_info_returns_none(self) -> None:
        self.assertIsNone(captions.select_caption_track({}, "en"))

    def test_ignores_tracks_without_url(self) -> None:
        info = {"subtitles": {"en": [{"ext": "vtt"}]}}  # no 'url'
        self.assertIsNone(captions.select_caption_track(info, "en"))


if __name__ == "__main__":
    unittest.main()
