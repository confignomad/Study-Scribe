"""AI study-guide prompt generation (Phase 10).

Rather than calling an AI directly, StudyScribe produces a **paste-ready**
Markdown file per transcript: a structured study-guide prompt (the sections
from the project spec) with the transcript embedded. The user pastes it into
Claude, ChatGPT, Gemini, or any other assistant — matching the master spec's
"import into an AI" workflow. No API key, no dependency, no cost.

Pure/testable: ``build_study_guide_prompt`` assembles the text; only
``write_study_guide_prompt`` touches the filesystem.
"""

from __future__ import annotations

from pathlib import Path

from app.services.markdown_export import _CAPTION_TYPE, sanitize_filename, vtt_to_text
from app.services.playlist import PlaylistEntry, format_duration
from app.services.transcript_format import paragraphize
from app.utils.logger import get_logger

logger = get_logger(__name__)

# The instruction block pasted into the AI. Sections mirror the master spec's
# "professional study guide" list.
_STUDY_GUIDE_INSTRUCTIONS = """\
You are an expert technical instructor. Using ONLY the transcript below,
produce a professional, well-structured study guide in Markdown. Do not invent
facts that aren't supported by the transcript; where the transcript is unclear,
say so. Use clear headings and concise, exam-focused language.

Include these sections, in order:

1. **Video Information** — title, source, and a one-paragraph overview.
2. **Learning Objectives** — what the learner should be able to do afterward.
3. **Clean Study Transcript** — the transcript rewritten into clear, readable
   prose (fix obvious speech-to-text errors; keep all technical content).
4. **Technical Notes** — key concepts, definitions, and mechanisms explained.
5. **Best Practices** — recommended approaches drawn from the material.
6. **Relevant RFC / Standards References** — cite any that apply (note if inferred).
7. **Common Mistakes** — pitfalls and misconceptions to avoid.
8. **Exam Tips** — targeted tips for a certification/exam context.
9. **Real-World Considerations** — how this applies in practice.
10. **Key Takeaways** — a short bulleted summary.
11. **Flashcards** — 8-15 Q&A pairs for spaced repetition.
12. **Review Questions** — 5-10 questions (with an answer key at the end).
"""


def build_study_guide_prompt(
    title: str,
    metadata: list[tuple[str, str]],
    transcript: str,
) -> str:
    """Assemble the full paste-ready study-guide prompt document."""
    meta_lines = "\n".join(f"- **{label}:** {value}" for label, value in metadata)
    body = transcript.strip() or "_(No transcript text could be extracted.)_"
    return (
        f"# Study Guide Prompt — {title}\n\n"
        "Paste everything below (from the horizontal rule down) into Claude, "
        "ChatGPT, Gemini, or another AI assistant to generate the study guide.\n\n"
        "---\n\n"
        f"{_STUDY_GUIDE_INSTRUCTIONS}\n"
        "## Video\n\n"
        f"{meta_lines}\n\n"
        "## Transcript\n\n"
        f"{body}\n"
    )


def write_study_guide_prompt(
    entry: PlaylistEntry,
    caption_result,
    dest_dir: str,
    *,
    date_str: str,
    language_display: str,
    numbered: bool,
    body_override: str | None = None,
) -> Path:
    """Write the paste-ready study-guide prompt for one video.

    Written UTF-8 with BOM (Sublime-friendly). Returns the path.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if body_override is not None:
        transcript = body_override
    else:
        raw = ""
        if caption_result.path:
            raw = Path(caption_result.path).read_text(encoding="utf-8", errors="replace")
        transcript = paragraphize(vtt_to_text(raw))

    metadata = [
        ("Title", entry.title),
        ("Length", format_duration(entry.duration)),
        ("Source", entry.url),
        ("Downloaded", date_str),
        ("Language", language_display),
        ("Caption Type", _CAPTION_TYPE.get(caption_result.kind or "", "Unknown")),
    ]
    document = build_study_guide_prompt(entry.title, metadata, transcript)

    stem = sanitize_filename(entry.title)
    base = f"{entry.position:02d} - {stem}" if numbered else stem
    path = dest / f"{base} (Study Guide Prompt).md"
    path.write_text(document, encoding="utf-8-sig")
    logger.info("Wrote study-guide prompt %s", path)
    return path
