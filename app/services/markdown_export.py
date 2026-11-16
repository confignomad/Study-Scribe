"""Markdown generation from raw caption files (Phase 6).

Turns a raw ``.vtt`` caption file into a clean, readable Markdown transcript
with a metadata header, saved under a per-playlist folder with a sanitized,
order-preserving filename.

Scope boundary: this produces the *clean* transcript (tags/timestamps stripped,
rolling-caption duplicates removed) as one flowing block. Paragraph reflow,
filler-word removal, and intro/outro/ad trimming belong to Phase 7. The raw
``.vtt`` stays on disk as the timestamped source of truth.

Pure, unit-testable helpers: ``vtt_to_text``, ``sanitize_filename``,
``build_markdown``. Only ``write_video_markdown`` / ``write_playlist_index``
touch the filesystem.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from app.services.playlist import PlaylistEntry, format_duration
from app.services.transcript_format import paragraphize, speechify_clean
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Inline VTT markup: timestamp tags <00:00:01.234> and <c>...</c> styling.
_TAG_RE = re.compile(r"<[^>]+>")
# Characters illegal in Windows filenames (also covers control chars).
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows reserved device names.
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_CAPTION_TYPE = {"manual": "Manual", "auto": "Auto-generated"}


def vtt_to_text(content: str) -> str:
    """Extract clean transcript text from WebVTT caption content.

    Drops headers, cue timing lines, and cue indices; strips inline timing/style
    tags; unescapes HTML entities; and collapses the rolling duplicate lines that
    YouTube auto-captions produce (each cue repeats the previous line). Returns a
    single space-joined block.
    """
    out: list[str] = []
    last: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("WEBVTT"):
            continue
        if line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        if "-->" in line:  # cue timing line
            continue
        if line.isdigit():  # cue sequence number
            continue

        text = _TAG_RE.sub("", line)
        text = html.unescape(text).strip()
        if not text:
            continue
        if text != last:  # collapse rolling duplicates
            out.append(text)
            last = text

    return " ".join(out)


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Return a filesystem-safe filename stem (no extension).

    Removes characters illegal on Windows/macOS/Linux, collapses whitespace,
    trims trailing dots/spaces, guards Windows reserved names, and truncates.
    """
    name = (name or "").replace("\n", " ").replace("\r", " ")
    name = _INVALID_FILENAME.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(". ")
    if not name:
        return "untitled"
    if name.upper() in _RESERVED_NAMES:
        name = f"_{name}"
    return name[:max_len].rstrip(". ") or "untitled"


def build_markdown(
    title: str,
    duration_str: str,
    source_url: str,
    date_str: str,
    language: str,
    caption_type: str,
    transcript: str,
) -> str:
    """Assemble the Markdown document (metadata header + transcript body)."""
    body = transcript.strip() or "_(No transcript text could be extracted.)_"
    return (
        f"# {title}\n\n"
        f"**Length:** {duration_str}  \n"
        f"**Source:** {source_url}  \n"
        f"**Downloaded:** {date_str}  \n"
        f"**Language:** {language}  \n"
        f"**Caption Type:** {caption_type}\n\n"
        f"---\n\n"
        f"{body}\n"
    )


def write_video_markdown(
    entry: PlaylistEntry,
    caption_result,
    dest_dir: str,
    *,
    date_str: str,
    language_display: str,
    numbered: bool,
    speechify: bool = False,
    body_override: str | None = None,
) -> Path:
    """Read the raw caption file for ``entry`` and write its Markdown transcript.

    ``speechify=False`` writes the standard readable transcript (sentences
    reflowed into paragraphs). ``speechify=True`` writes a TTS-tuned variant
    (fillers/intros/outros trimmed, shorter paragraphs) to a "(Speechify)" file.
    ``body_override`` supplies a pre-built body (e.g. a bilingual document,
    Phase 9); when given, the raw file is not re-parsed.

    Files are written UTF-8 **with BOM** so editors like Sublime (which default
    to Windows-1252) detect the encoding and render non-ASCII text correctly.
    Returns the path written. Raises on I/O errors (caller logs/handles).
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if body_override is not None:
        body = body_override
    else:
        raw = ""
        if caption_result.path:
            raw = Path(caption_result.path).read_text(encoding="utf-8", errors="replace")
        transcript = vtt_to_text(raw)
        body = speechify_clean(transcript) if speechify else paragraphize(transcript)

    caption_type = _CAPTION_TYPE.get(caption_result.kind or "", "Unknown")
    markdown = build_markdown(
        title=entry.title,
        duration_str=format_duration(entry.duration),
        source_url=entry.url,
        date_str=date_str,
        language=language_display,
        caption_type=caption_type,
        transcript=body,
    )

    stem = sanitize_filename(entry.title)
    base = f"{entry.position:02d} - {stem}" if numbered else stem
    suffix = " (Speechify)" if speechify else ""
    path = dest / f"{base}{suffix}.md"
    path.write_text(markdown, encoding="utf-8-sig")
    logger.info("Wrote Markdown %s", path)
    return path


def _body_from_vtt(path: str | None) -> str:
    """Read a raw .vtt file and return its clean, paragraphized transcript."""
    raw = ""
    if path:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    return paragraphize(vtt_to_text(raw)) or "_(No transcript text could be extracted.)_"


def build_bilingual_body(
    original_path: str | None, original_label: str,
    translated_path: str | None, translated_label: str,
) -> str:
    """Combine two raw caption files into one labeled bilingual Markdown body."""
    return (
        f"## Original — {original_label}\n\n{_body_from_vtt(original_path)}\n\n"
        f"## Translated — {translated_label}\n\n{_body_from_vtt(translated_path)}"
    )


def write_playlist_index(playlist_title: str, items: list[tuple[int, str, str]], dest_dir: str) -> Path:
    """Write a README.md index for a playlist.

    ``items`` is a list of (position, title, md_filename). Returns the path.
    """
    lines = [f"# {playlist_title}", "", f"{len(items)} transcript(s).", ""]
    for position, title, filename in items:
        lines.append(f"{position}. [{title}](<{filename}>)")
    path = Path(dest_dir) / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    logger.info("Wrote playlist index %s", path)
    return path
