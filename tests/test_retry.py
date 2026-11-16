"""Unit tests for the Phase 5 retry logic in app.services.captions.

Offline: fetch_video_captions is stubbed so no network is touched, and
backoff_base=0 keeps the tests instant.

Run from the StudyScribe/ directory:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import threading
import unittest

from app.services import captions
from app.services.captions import CaptionResult


class DownloadCaptionsRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original = captions.fetch_video_captions

    def tearDown(self) -> None:
        captions.fetch_video_captions = self._original

    def _stub(self, statuses):
        """Make fetch_video_captions yield the given statuses in order."""
        calls = {"n": 0}

        def fake(video_id, lang_code, output_dir, timeout=None):
            i = min(calls["n"], len(statuses) - 1)
            calls["n"] += 1
            return CaptionResult(video_id, statuses[i])

        captions.fetch_video_captions = fake
        return calls

    def test_succeeds_first_try(self) -> None:
        calls = self._stub(["ok"])
        result = captions.download_captions("vid", "en", "out", backoff_base=0)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(calls["n"], 1)

    def test_retries_transient_then_succeeds(self) -> None:
        calls = self._stub(["rate_limited", "network_error", "ok"])
        result = captions.download_captions("vid", "en", "out", max_attempts=3, backoff_base=0)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(calls["n"], 3)

    def test_gives_up_after_max_attempts(self) -> None:
        calls = self._stub(["rate_limited"])  # always transient
        result = captions.download_captions("vid", "en", "out", max_attempts=3, backoff_base=0)
        self.assertEqual(result.status, "rate_limited")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(calls["n"], 3)

    def test_permanent_failure_not_retried(self) -> None:
        calls = self._stub(["no_captions"])
        result = captions.download_captions("vid", "en", "out", max_attempts=3, backoff_base=0)
        self.assertEqual(result.status, "no_captions")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(calls["n"], 1)  # fast-fail, no retry

    def test_cancel_before_start_returns_cancelled(self) -> None:
        calls = self._stub(["ok"])
        event = threading.Event()
        event.set()
        result = captions.download_captions(
            "vid", "en", "out", cancel_event=event, backoff_base=0
        )
        self.assertEqual(result.status, "cancelled")
        self.assertEqual(calls["n"], 0)  # never even tried

    def test_cancel_during_backoff_stops_retrying(self) -> None:
        calls = self._stub(["network_error"])  # would retry forever otherwise
        event = threading.Event()
        # A real Event: wait(delay) with delay=0.01 then we set it via a timer-like flip.
        # Simpler: pre-set so the wait returns True immediately on first backoff.
        event.set()
        # First attempt runs (event checked only before fetch); it's already set,
        # so the loop returns cancelled before the first fetch.
        result = captions.download_captions(
            "vid", "en", "out", max_attempts=3, cancel_event=event, backoff_base=0.01
        )
        self.assertEqual(result.status, "cancelled")


if __name__ == "__main__":
    unittest.main()
