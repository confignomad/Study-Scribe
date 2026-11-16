"""Unit tests for app.services.exporter (Phase 8). Offline.

TXT/HTML need no third-party libs. DOCX/PDF tests skip if the libs are absent.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services import exporter
from app.services.captions import CaptionResult
from app.services.playlist import PlaylistEntry

RAW_VTT = (
    "WEBVTT\n\n"
    "00:00:00.000 --> 00:00:02.000\n"
    "The RIB holds all routes. The FIB is derived from it.\n\n"
    "00:00:02.000 --> 00:00:04.000\n"
    "It is optimized for fast lookup. für Übung.\n"
)


def _fixture():
    tmp = tempfile.mkdtemp(prefix="ss_exp_")
    raw = Path(tmp) / "cap.vtt"
    raw.write_text(RAW_VTT, encoding="utf-8")
    entry = PlaylistEntry(position=3, video_id="vid", title="OSPF: Basics?", url="https://x", duration=587)
    result = CaptionResult("vid", "ok", kind="auto", language="en", path=str(raw))
    return tmp, entry, result


class ExportTxtHtmlTests(unittest.TestCase):
    def test_txt_and_html_written(self) -> None:
        tmp, entry, result = _fixture()
        res = exporter.export_video(
            entry, result, tmp, formats={"TXT", "HTML"},
            date_str="2026-06-30", language_display="English", numbered=True,
        )
        self.assertEqual(res, {"TXT": True, "HTML": True})
        txt = Path(tmp) / "03 - OSPF Basics.txt"
        htm = Path(tmp) / "03 - OSPF Basics.html"
        self.assertTrue(txt.exists() and htm.exists())

        txt_content = txt.read_text(encoding="utf-8-sig")
        self.assertIn("OSPF: Basics?", txt_content)
        self.assertIn("Length: 9:47", txt_content)
        self.assertIn("für Übung", txt_content)  # UTF-8 round-trip

        html_content = htm.read_text(encoding="utf-8")
        self.assertIn("<h1>OSPF: Basics?</h1>", html_content)
        self.assertIn("<p>", html_content)
        self.assertIn('charset="utf-8"', html_content)

    def test_html_escapes_special_chars(self) -> None:
        tmp, entry, result = _fixture()
        entry.title = "A <b> & C"
        exporter.export_video(
            entry, result, tmp, formats={"HTML"},
            date_str="d", language_display="English", numbered=False,
        )
        content = (Path(tmp) / "A b & C.html").read_text(encoding="utf-8")
        self.assertIn("A &lt;b&gt; &amp; C", content)


class ExportDocxPdfTests(unittest.TestCase):
    def test_docx_written(self) -> None:
        try:
            import docx  # noqa: F401
        except ImportError:
            self.skipTest("python-docx not installed")
        tmp, entry, result = _fixture()
        res = exporter.export_video(
            entry, result, tmp, formats={"DOCX"},
            date_str="2026-06-30", language_display="English", numbered=True,
        )
        self.assertTrue(res["DOCX"])
        docx_path = Path(tmp) / "03 - OSPF Basics.docx"
        self.assertTrue(docx_path.exists() and docx_path.stat().st_size > 0)

    def test_pdf_written(self) -> None:
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab not installed")
        tmp, entry, result = _fixture()
        res = exporter.export_video(
            entry, result, tmp, formats={"PDF"},
            date_str="2026-06-30", language_display="English", numbered=True,
        )
        self.assertTrue(res["PDF"])
        pdf_path = Path(tmp) / "03 - OSPF Basics.pdf"
        self.assertTrue(pdf_path.exists())
        self.assertEqual(pdf_path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
