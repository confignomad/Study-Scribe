"""Document export (Phase 8): Markdown transcript -> PDF / DOCX / TXT / HTML.

Exports mirror the standard clean transcript (same paragraphed body as the
canonical Markdown) plus the metadata header. Markdown remains the source of
truth; this module only produces the additional shareable formats.

Heavy libraries (reportlab, python-docx) are imported lazily inside their
writers, so the app and the offline TXT/HTML tests don't require them unless
those formats are actually requested.
"""

from __future__ import annotations

import html
from pathlib import Path

from app.services.markdown_export import _CAPTION_TYPE, sanitize_filename, vtt_to_text
from app.services.playlist import format_duration
from app.services.transcript_format import paragraphize
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Export labels this module handles (Markdown/Speechify are done elsewhere).
EXPORT_LABELS = ("PDF", "DOCX", "TXT", "HTML")

_EXT = {"PDF": ".pdf", "DOCX": ".docx", "TXT": ".txt", "HTML": ".html"}


def _metadata(entry, caption_result, date_str: str, language_display: str) -> list[tuple[str, str]]:
    return [
        ("Length", format_duration(entry.duration)),
        ("Source", entry.url),
        ("Downloaded", date_str),
        ("Language", language_display),
        ("Caption Type", _CAPTION_TYPE.get(caption_result.kind or "", "Unknown")),
    ]


# --- Per-format writers ----------------------------------------------------
def _write_txt(path: Path, title: str, meta, paragraphs) -> None:
    lines = [title, ""]
    lines += [f"{label}: {value}" for label, value in meta]
    lines += ["", "-" * 40, ""]
    lines.append("\n\n".join(paragraphs))
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def _write_html(path: Path, title: str, meta, paragraphs) -> None:
    esc = html.escape
    meta_items = "".join(f"<li><strong>{esc(l)}:</strong> {esc(v)}</li>" for l, v in meta)
    body = "\n".join(f"<p>{esc(p)}</p>" for p in paragraphs)
    doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        f"<title>{esc(title)}</title>\n"
        "<style>body{font-family:system-ui,Arial,sans-serif;max-width:800px;"
        "margin:2rem auto;padding:0 1rem;line-height:1.6}"
        ".meta{color:#555;list-style:none;padding:0}</style>\n"
        "</head><body>\n"
        f"<h1>{esc(title)}</h1>\n"
        f'<ul class="meta">{meta_items}</ul>\n<hr>\n'
        f"{body}\n"
        "</body></html>\n"
    )
    path.write_text(doc, encoding="utf-8")


def _write_docx(path: Path, title: str, meta, paragraphs) -> None:
    from docx import Document  # lazy

    document = Document()
    document.add_heading(title, level=1)
    for label, value in meta:
        para = document.add_paragraph()
        para.add_run(f"{label}: ").bold = True
        para.add_run(value)
    document.add_paragraph()
    for para in paragraphs:
        document.add_paragraph(para)
    document.save(str(path))


def _pdf_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _write_pdf(path: Path, title: str, meta, paragraphs) -> None:
    from reportlab.lib.pagesizes import letter  # lazy
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    story = [Paragraph(_pdf_escape(title), styles["Title"]), Spacer(1, 0.15 * inch)]
    for label, value in meta:
        story.append(Paragraph(f"<b>{_pdf_escape(label)}:</b> {_pdf_escape(value)}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))
    for para in paragraphs:
        story.append(Paragraph(_pdf_escape(para), styles["BodyText"]))
        story.append(Spacer(1, 0.10 * inch))
    SimpleDocTemplate(str(path), pagesize=letter, title=title).build(story)


_WRITERS = {"TXT": _write_txt, "HTML": _write_html, "DOCX": _write_docx, "PDF": _write_pdf}


def export_video(
    entry,
    caption_result,
    dest_dir: str,
    *,
    formats,
    date_str: str,
    language_display: str,
    numbered: bool,
    body_override: str | None = None,
) -> dict[str, bool]:
    """Write the requested export ``formats`` for one video.

    ``formats`` is an iterable of labels among ``EXPORT_LABELS``. ``body_override``
    supplies pre-built body text (e.g. a bilingual document, Phase 9). Returns
    ``{label: True|False}`` (False = that format failed; logged, never raised).
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if body_override is not None:
        source_text = body_override
    else:
        raw = ""
        if caption_result.path:
            raw = Path(caption_result.path).read_text(encoding="utf-8", errors="replace")
        source_text = paragraphize(vtt_to_text(raw))
    paragraphs = [p.strip() for p in source_text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = ["(No transcript text could be extracted.)"]

    meta = _metadata(entry, caption_result, date_str, language_display)
    stem = sanitize_filename(entry.title)
    base = f"{entry.position:02d} - {stem}" if numbered else stem

    results: dict[str, bool] = {}
    for label in formats:
        writer = _WRITERS.get(label)
        if writer is None:
            continue
        path = dest / f"{base}{_EXT[label]}"
        try:
            writer(path, entry.title, meta, paragraphs)
            logger.info("Wrote %s export %s", label, path)
            results[label] = True
        except Exception:  # noqa: BLE001 - one bad format must not stop the others
            logger.exception("%s export failed for %s", label, entry.video_id)
            results[label] = False
    return results
