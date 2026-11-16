"""Unit tests for app.services.study_guide (Phase 10). Offline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services import study_guide as sg
from app.services.captions import CaptionResult
from app.services.playlist import PlaylistEntry


class BuildStudyGuidePromptTests(unittest.TestCase):
    def _prompt(self) -> str:
        return sg.build_study_guide_prompt(
            "OSPF Fundamentals",
            [("Title", "OSPF Fundamentals"), ("Source", "https://youtu.be/x")],
            "The RIB holds all routes.",
        )

    def test_has_paste_marker_and_transcript(self) -> None:
        out = self._prompt()
        self.assertIn("# Study Guide Prompt — OSPF Fundamentals", out)
        self.assertIn("The RIB holds all routes.", out)
        self.assertIn("## Transcript", out)
        self.assertIn("**Source:** https://youtu.be/x", out)

    def test_includes_all_spec_sections(self) -> None:
        out = self._prompt()
        for section in (
            "Learning Objectives", "Clean Study Transcript", "Technical Notes",
            "Relevant RFC", "Common Mistakes", "Exam Tips", "Key Takeaways",
            "Flashcards", "Review Questions",
        ):
            with self.subTest(section=section):
                self.assertIn(section, out)

    def test_empty_transcript_placeholder(self) -> None:
        out = sg.build_study_guide_prompt("T", [], "")
        self.assertIn("No transcript text", out)


class WriteStudyGuidePromptTests(unittest.TestCase):
    def test_writes_bom_file_with_expected_name(self) -> None:
        tmp = tempfile.mkdtemp(prefix="ss_sg_")
        raw = Path(tmp) / "cap.vtt"
        raw.write_text(
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nfür Übung. RIB and FIB.\n",
            encoding="utf-8",
        )
        entry = PlaylistEntry(position=5, video_id="v", title="OSPF: Deep/Dive?", url="https://x", duration=600)
        result = CaptionResult("v", "ok", kind="auto", language="en", path=str(raw))

        out = sg.write_study_guide_prompt(
            entry, result, tmp, date_str="2026-06-30",
            language_display="English", numbered=True,
        )
        self.assertEqual(out.name, "05 - OSPF DeepDive (Study Guide Prompt).md")
        self.assertEqual(out.read_bytes()[:3], b"\xef\xbb\xbf")  # UTF-8 BOM
        content = out.read_text(encoding="utf-8-sig")
        self.assertIn("für Übung", content)  # UTF-8 round-trip
        self.assertIn("Flashcards", content)

    def test_body_override_used_verbatim(self) -> None:
        tmp = tempfile.mkdtemp(prefix="ss_sg2_")
        entry = PlaylistEntry(position=1, video_id="v", title="T", url="https://x", duration=60)
        result = CaptionResult("v", "ok", kind="manual", language="en", path=None)
        out = sg.write_study_guide_prompt(
            entry, result, tmp, date_str="d", language_display="English",
            numbered=False, body_override="OVERRIDE BODY TEXT",
        )
        self.assertIn("OVERRIDE BODY TEXT", out.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
