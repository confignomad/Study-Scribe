"""Unit tests for app.services.markdown_export (Phase 6). Offline."""

from __future__ import annotations

import unittest

from app.services import markdown_export as md

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.240 --> 00:00:01.750 align:start position:0%

Hello.<00:00:00.719><c> Today</c><00:00:00.960><c> we'll</c>

00:00:01.750 --> 00:00:01.760 align:start position:0%
Hello. Today we'll


00:00:01.760 --> 00:00:04.150 align:start position:0%
Hello. Today we'll
practice<00:00:02.159><c> questions</c>

00:00:04.150 --> 00:00:05.000 align:start position:0%
practice questions
"""


class VttToTextTests(unittest.TestCase):
    def test_strips_headers_timings_tags_and_dedupes(self) -> None:
        text = md.vtt_to_text(ROLLING_VTT)
        self.assertEqual(text, "Hello. Today we'll practice questions")
        self.assertNotIn("WEBVTT", text)
        self.assertNotIn("-->", text)
        self.assertNotIn("<c>", text)

    def test_unescapes_entities(self) -> None:
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nAT&amp;T &lt;router&gt;\n"
        self.assertEqual(md.vtt_to_text(vtt), "AT&T <router>")

    def test_empty_input(self) -> None:
        self.assertEqual(md.vtt_to_text("WEBVTT\n\n"), "")


class SanitizeFilenameTests(unittest.TestCase):
    def test_removes_illegal_characters(self) -> None:
        self.assertEqual(md.sanitize_filename('a/b:c*d?"e'), "abcde")

    def test_collapses_whitespace_and_trims_dots(self) -> None:
        self.assertEqual(md.sanitize_filename("  OSPF   Fundamentals... "), "OSPF Fundamentals")

    def test_reserved_name_is_guarded(self) -> None:
        self.assertEqual(md.sanitize_filename("CON"), "_CON")

    def test_empty_becomes_untitled(self) -> None:
        self.assertEqual(md.sanitize_filename("///"), "untitled")

    def test_truncates_length(self) -> None:
        self.assertEqual(len(md.sanitize_filename("x" * 500, max_len=120)), 120)


class BuildMarkdownTests(unittest.TestCase):
    def test_contains_all_metadata_fields(self) -> None:
        out = md.build_markdown(
            title="OSPF Fundamentals",
            duration_str="9:47",
            source_url="https://youtu.be/abc",
            date_str="2026-06-30",
            language="English",
            caption_type="Auto-generated",
            transcript="hello world",
        )
        self.assertIn("# OSPF Fundamentals", out)
        self.assertIn("**Length:** 9:47", out)
        self.assertIn("**Source:** https://youtu.be/abc", out)
        self.assertIn("**Downloaded:** 2026-06-30", out)
        self.assertIn("**Language:** English", out)
        self.assertIn("**Caption Type:** Auto-generated", out)
        self.assertIn("hello world", out)

    def test_empty_transcript_has_placeholder(self) -> None:
        out = md.build_markdown("T", "—", "u", "d", "English", "Manual", "")
        self.assertIn("No transcript text", out)


class WriteVideoMarkdownTests(unittest.TestCase):
    def test_writes_numbered_utf8_file(self) -> None:
        import tempfile
        from pathlib import Path

        from app.services.captions import CaptionResult
        from app.services.playlist import PlaylistEntry

        tmp = tempfile.mkdtemp(prefix="ss_md_")
        # Write a raw vtt with a non-ASCII (German) word to prove UTF-8 round-trip.
        raw = Path(tmp) / "raw.vtt"
        raw.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nfür Übung\n", encoding="utf-8")

        entry = PlaylistEntry(position=2, video_id="v", title="OSPF: Basics?", url="https://x", duration=587)
        result = CaptionResult("v", "ok", kind="auto", language="de", path=str(raw))

        out = md.write_video_markdown(
            entry, result, tmp, date_str="2026-06-30", language_display="German", numbered=True
        )
        self.assertEqual(out.name, "02 - OSPF Basics.md")  # ':' and '?' stripped
        content = out.read_text(encoding="utf-8")
        self.assertIn("für Übung", content)          # correct UTF-8
        self.assertIn("**Caption Type:** Auto-generated", content)
        self.assertIn("**Length:** 9:47", content)


if __name__ == "__main__":
    unittest.main()
