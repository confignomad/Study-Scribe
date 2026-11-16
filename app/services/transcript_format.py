"""Transcript formatting for readability + Speechify/TTS (Phase 7).

All functions are pure and unit-tested offline. They operate on the clean
transcript text produced by ``markdown_export.vtt_to_text``:

* ``paragraphize``      - group sentences into readable paragraphs (used for the
                          standard Markdown so it's no longer one wall of text).
* ``speechify_clean``   - trim intros/outros/ads, drop filler words, and reflow
                          into shorter listener-friendly paragraphs.

Fenced code blocks (```...```) are preserved verbatim — never reflowed — so any
CLI/code stays intact.
"""

from __future__ import annotations

import re

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sentence boundary: end punctuation followed by space then a capital/digit/quote.
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=["A-Z0-9])')
# Spoken fillers as standalone words (um, umm, uh, uhh, er, erm, hmm).
_FILLER = re.compile(r'\b(?:um+|uh+|erm?|hmm+)\b[,]?\s*', re.IGNORECASE)
_MULTISPACE = re.compile(r"[ \t]{2,}")
_CODE_FENCE = re.compile(r"(```.*?```)", re.DOTALL)

# Sentences matching any of these (English) are treated as intro/outro/ad noise.
_OUTRO_PATTERNS = [
    re.compile(r"\b(?:like and subscribe|don'?t forget to subscribe)\b", re.I),
    re.compile(r"\bplease\b.*\bsubscribe\b", re.I),
    re.compile(r"\bif you (?:like|liked|enjoy|enjoyed) (?:the|this) video\b", re.I),
    re.compile(r"\bthanks?(?: so much)? for watching\b", re.I),
    re.compile(r"\bsee you (?:in|on) the next|see you next time\b", re.I),
    re.compile(r"^\s*(?:goodbye|bye)\b", re.I),
    re.compile(r"\bhit the (?:like|bell)\b", re.I),
]


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences (naive but robust for caption text)."""
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]


def _paragraphize_prose(text: str, sentences_per_para: int, max_chars: int) -> str:
    """Group a prose segment's sentences into blank-line-separated paragraphs."""
    sentences = split_sentences(text)
    paragraphs: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        current.append(sentence)
        current_len += len(sentence)
        if len(current) >= sentences_per_para or current_len >= max_chars:
            paragraphs.append(" ".join(current))
            current, current_len = [], 0
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def paragraphize(text: str, sentences_per_para: int = 3, max_chars: int = 500) -> str:
    """Reflow ``text`` into paragraphs, leaving fenced code blocks untouched."""
    segments = _CODE_FENCE.split(text)
    out: list[str] = []
    for segment in segments:
        if segment.startswith("```"):
            out.append(segment.strip())
        else:
            formatted = _paragraphize_prose(segment, sentences_per_para, max_chars)
            if formatted:
                out.append(formatted)
    return "\n\n".join(out)


def remove_fillers(text: str) -> str:
    """Remove standalone filler words and tidy the resulting spacing."""
    text = _FILLER.sub("", text)
    text = _MULTISPACE.sub(" ", text)
    # Clean up spaces left before punctuation.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def trim_intro_outro(text: str) -> str:
    """Drop sentences that look like intros/outros/ads (English heuristics)."""
    kept = [
        sentence
        for sentence in split_sentences(text)
        if not any(pattern.search(sentence) for pattern in _OUTRO_PATTERNS)
    ]
    return " ".join(kept)


def speechify_clean(text: str) -> str:
    """Full Speechify pass: trim boilerplate, drop fillers, short paragraphs."""
    text = trim_intro_outro(text)
    text = remove_fillers(text)
    return paragraphize(text, sentences_per_para=2, max_chars=350)
