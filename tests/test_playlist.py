"""Unit tests for app.services.playlist (Phase 3).

Offline only: the pure transform (entries_from_info) and format_duration are
exercised against a hand-built yt-dlp-style info dict. fetch_playlist's network
path is not called here.

Run from the StudyScribe/ directory:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from app.services import playlist


class FormatDurationTests(unittest.TestCase):
    def test_none_is_dash(self) -> None:
        self.assertEqual(playlist.format_duration(None), "—")

    def test_minutes_seconds(self) -> None:
        self.assertEqual(playlist.format_duration(587), "9:47")

    def test_pads_seconds(self) -> None:
        self.assertEqual(playlist.format_duration(65), "1:05")

    def test_hours(self) -> None:
        self.assertEqual(playlist.format_duration(3725), "1:02:05")


class EntriesFromInfoTests(unittest.TestCase):
    def _sample_info(self) -> dict:
        return {
            "id": "PL123",
            "title": "CCNP ENCOR",
            "entries": [
                {"id": "aaaaaaaaaaa", "title": "Introduction", "duration": 587},
                None,  # yt-dlp yields None for unavailable/removed entries
                {"id": "bbbbbbbbbbb", "title": "OSPF Fundamentals", "duration": 842,
                 "url": "https://www.youtube.com/watch?v=bbbbbbbbbbb"},
                {"id": "", "title": "no id — skipped"},
            ],
        }

    def test_skips_empty_and_idless_entries(self) -> None:
        entries = playlist.entries_from_info(self._sample_info())
        self.assertEqual(len(entries), 2)

    def test_positions_are_sequential_after_skips(self) -> None:
        entries = playlist.entries_from_info(self._sample_info())
        self.assertEqual([e.position for e in entries], [1, 2])

    def test_fields_mapped(self) -> None:
        first = playlist.entries_from_info(self._sample_info())[0]
        self.assertEqual(first.video_id, "aaaaaaaaaaa")
        self.assertEqual(first.title, "Introduction")
        self.assertEqual(first.duration, 587)
        self.assertEqual(first.caption_status, "unknown")

    def test_url_synthesized_when_missing(self) -> None:
        first = playlist.entries_from_info(self._sample_info())[0]
        self.assertEqual(first.url, "https://www.youtube.com/watch?v=aaaaaaaaaaa")

    def test_empty_playlist_yields_no_entries(self) -> None:
        self.assertEqual(playlist.entries_from_info({"entries": []}), [])


if __name__ == "__main__":
    unittest.main()
