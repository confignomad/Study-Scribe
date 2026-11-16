"""Unit tests for app.services.youtube (Phase 2).

These tests are offline: the pure parser is exercised directly, and the one
network-dependent function (check_video_availability) is monkeypatched so the
end-to-end validator can be tested without hitting YouTube.

Run from the StudyScribe/ directory:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from app.services import youtube

VALID_ID = "dQw4w9WgXcQ"  # 11 chars — a well-formed (example) video ID


class ParseYouTubeURLTests(unittest.TestCase):
    def test_standard_watch_url(self) -> None:
        parsed = youtube.parse_youtube_url(f"https://www.youtube.com/watch?v={VALID_ID}")
        self.assertEqual(parsed.kind, "video")
        self.assertEqual(parsed.video_id, VALID_ID)

    def test_short_youtu_be_url(self) -> None:
        parsed = youtube.parse_youtube_url(f"https://youtu.be/{VALID_ID}?si=abc")
        self.assertEqual(parsed.kind, "video")
        self.assertEqual(parsed.video_id, VALID_ID)

    def test_shorts_and_embed(self) -> None:
        for url in (
            f"https://www.youtube.com/shorts/{VALID_ID}",
            f"https://www.youtube.com/embed/{VALID_ID}",
        ):
            with self.subTest(url=url):
                self.assertEqual(youtube.parse_youtube_url(url).video_id, VALID_ID)

    def test_missing_scheme_is_accepted(self) -> None:
        parsed = youtube.parse_youtube_url(f"youtube.com/watch?v={VALID_ID}")
        self.assertEqual(parsed.kind, "video")
        self.assertEqual(parsed.video_id, VALID_ID)

    def test_video_with_playlist_param_is_video(self) -> None:
        parsed = youtube.parse_youtube_url(
            f"https://www.youtube.com/watch?v={VALID_ID}&list=PL123456789"
        )
        self.assertEqual(parsed.kind, "video")
        self.assertEqual(parsed.video_id, VALID_ID)
        self.assertEqual(parsed.playlist_id, "PL123456789")

    def test_playlist_only_url(self) -> None:
        parsed = youtube.parse_youtube_url(
            "https://www.youtube.com/playlist?list=PL123456789"
        )
        self.assertEqual(parsed.kind, "playlist")
        self.assertEqual(parsed.playlist_id, "PL123456789")

    def test_non_youtube_host_is_invalid(self) -> None:
        self.assertEqual(youtube.parse_youtube_url("https://vimeo.com/12345").kind, "invalid")

    def test_malformed_video_id_is_invalid(self) -> None:
        self.assertEqual(youtube.parse_youtube_url("https://www.youtube.com/watch?v=short").kind, "invalid")

    def test_empty_and_garbage(self) -> None:
        for url in ("", "   ", "hello world", "https://www.youtube.com/"):
            with self.subTest(url=url):
                self.assertEqual(youtube.parse_youtube_url(url).kind, "invalid")


class ValidateSingleVideoTests(unittest.TestCase):
    """End-to-end validator with the network layer stubbed out."""

    def test_invalid_url_short_circuits_without_network(self) -> None:
        # If this touched the network it would fail; a stub guards that.
        youtube.check_video_availability = _fail_if_called
        result = youtube.validate_single_video("not a url")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "invalid")

    def test_playlist_url_points_to_phase_3(self) -> None:
        youtube.check_video_availability = _fail_if_called
        result = youtube.validate_single_video(
            "https://www.youtube.com/playlist?list=PL123456789"
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "playlist")

    def test_valid_video_uses_availability_result(self) -> None:
        youtube.check_video_availability = lambda vid, timeout=None: {
            "status": "ok",
            "title": "Example Video",
            "author": "Example Channel",
        }
        result = youtube.validate_single_video(f"https://youtu.be/{VALID_ID}")
        self.assertTrue(result.ok)
        self.assertEqual(result.title, "Example Video")
        self.assertEqual(result.author, "Example Channel")
        self.assertEqual(result.video_id, VALID_ID)

    def test_unavailable_video_is_reported(self) -> None:
        youtube.check_video_availability = lambda vid, timeout=None: {
            "status": "unavailable",
            "message": "gone",
        }
        result = youtube.validate_single_video(f"https://youtu.be/{VALID_ID}")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "unavailable")

    def setUp(self) -> None:
        self._original = youtube.check_video_availability

    def tearDown(self) -> None:
        youtube.check_video_availability = self._original


def _fail_if_called(*_args, **_kwargs):  # pragma: no cover - guard stub
    raise AssertionError("Network check should not run for this input.")


if __name__ == "__main__":
    unittest.main()
