"""Caption download service (Phase 4).

Retrieves caption tracks for a single video and preserves the **raw** data on
disk, untouched, for later phases (cleanup in Phase 7, Markdown in Phase 6).

Strategy (no ffmpeg required):

1. Ask yt-dlp for the video's ``subtitles`` (manual) and ``automatic_captions``
   dictionaries via a metadata-only extraction.
2. Pick the best track for the requested language, preferring **manual** over
   auto-generated, and a text-friendly format (``vtt``) when available.
3. Download that track's bytes directly and write them to
   ``<output>/<raw subdir>/<video_id>.<lang>.<ext>``.

``select_caption_track`` is a pure function (unit-tested offline). Only
``fetch_video_captions`` touches the network / filesystem.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Preferred caption formats, most text-friendly first.
_EXT_PRIORITY = ("vtt", "srv3", "srv2", "srv1", "ttml", "json3")

# Statuses worth retrying — transient failures only. Everything else
# (no_captions, unavailable, private, generic error) is permanent.
_RETRYABLE = frozenset({"network_error", "rate_limited"})

# Sentinel lang_code meaning "the video's original/source language" (Phase 9).
ORIGINAL_LANG = "__original__"


def detect_original_language(info: dict) -> str | None:
    """Best-effort guess of a video's original (spoken) caption language.

    yt-dlp usually sets ``info["language"]``; otherwise fall back to the first
    manual subtitle track, then the first automatic-caption track.
    """
    lang = info.get("language")
    if lang:
        return lang
    for source in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        if source:
            return next(iter(source))
    return None


@dataclass
class CaptionResult:
    """Outcome of downloading captions for one video."""

    video_id: str
    status: str  # ok | no_captions | unavailable | rate_limited | network_error | error | cancelled
    kind: str | None = None       # "manual" | "auto"
    language: str | None = None   # the caption track's language key actually used
    path: str | None = None       # where the raw track was saved
    message: str = ""
    attempts: int = 1             # how many tries it took (set by download_captions)
    original_language: str | None = None  # detected source language (Phase 9)


def _pick_lang(source: dict, lang_code: str) -> tuple[str | None, list | None]:
    """Find the track list for ``lang_code`` in a captions dict.

    Matches an exact key first (e.g. ``"en"``), then a base-language prefix
    (``"en-US"``, ``"en-GB"``, ``"en.something"``) so regional variants resolve.
    """
    if not source:
        return None, None
    if lang_code in source:
        return lang_code, source[lang_code]
    for key, tracks in source.items():
        base = key.split("-")[0].split(".")[0].lower()
        if base == lang_code.lower():
            return key, tracks
    return None, None


def _pick_track(tracks: list | None) -> dict | None:
    """Choose the best-format track (by _EXT_PRIORITY) that has a URL."""
    if not tracks:
        return None
    by_ext = {t.get("ext"): t for t in tracks if t.get("url")}
    for ext in _EXT_PRIORITY:
        if ext in by_ext:
            return by_ext[ext]
    for track in tracks:  # any track with a URL, as a last resort
        if track.get("url"):
            return track
    return None


def select_caption_track(info: dict, lang_code: str) -> dict | None:
    """Select the best caption track for ``lang_code`` from a yt-dlp info dict.

    Prefers manual captions over auto-generated. Returns a dict with
    ``kind``/``language``/``ext``/``url`` keys, or ``None`` if the requested
    language has no captions at all.
    """
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    for kind, source in (("manual", manual), ("auto", auto)):
        matched_lang, tracks = _pick_lang(source, lang_code)
        track = _pick_track(tracks)
        if track:
            return {
                "kind": kind,
                "language": matched_lang,
                "ext": track.get("ext"),
                "url": track.get("url"),
            }
    return None


def _raw_dir(output_dir: str) -> Path:
    """Return (creating if needed) the raw-captions working directory."""
    directory = Path(output_dir) / settings.RAW_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def fetch_video_captions(
    video_id: str,
    lang_code: str,
    output_dir: str,
    timeout: float | None = None,
) -> CaptionResult:
    """Download and save the raw caption track for one video.

    Returns a :class:`CaptionResult`; failure modes (unavailable, no captions,
    network, write error) are reported via ``status`` rather than raised.
    """
    if timeout is None:
        timeout = settings.URL_CHECK_TIMEOUT

    import yt_dlp

    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": timeout,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.warning("Caption metadata unavailable for %s: %s", video_id, exc)
        return CaptionResult(video_id, "unavailable", message="Video unavailable or private.")
    except Exception as exc:  # noqa: BLE001 - report, never raise, per-video
        logger.exception("Unexpected error fetching caption metadata for %s", video_id)
        return CaptionResult(video_id, "error", message=str(exc))

    # Determine the effective language: an explicit code, or the video's
    # original language when the ORIGINAL_LANG sentinel is passed (Phase 9).
    original = detect_original_language(info or {})
    effective_lang = original if lang_code == ORIGINAL_LANG else lang_code
    if not effective_lang:
        return CaptionResult(
            video_id, "no_captions", original_language=original,
            message="Could not determine the video's original language.",
        )

    track = select_caption_track(info or {}, effective_lang)
    if not track:
        return CaptionResult(
            video_id, "no_captions", original_language=original,
            message=f"No '{effective_lang}' captions available for this video.",
        )

    try:
        request = Request(track["url"], headers={"User-Agent": settings.USER_AGENT})
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
    except HTTPError as exc:
        if exc.code == 429:
            logger.warning("Caption download rate-limited (429) for %s", video_id)
            return CaptionResult(video_id, "rate_limited", original_language=original,
                                 message="Rate-limited by YouTube (HTTP 429).")
        logger.warning("Caption download HTTP %s for %s", exc.code, video_id)
        return CaptionResult(video_id, "error", original_language=original,
                             message=f"Caption download failed (HTTP {exc.code}).")
    except (URLError, socket.timeout, TimeoutError) as exc:
        logger.warning("Caption download network error for %s: %s", video_id, exc)
        return CaptionResult(video_id, "network_error", original_language=original,
                             message="Could not download captions.")

    ext = track.get("ext") or "vtt"
    lang = track.get("language") or effective_lang
    path = _raw_dir(output_dir) / f"{video_id}.{lang}.{ext}"
    try:
        path.write_bytes(data)
    except OSError as exc:
        logger.exception("Could not write caption file %s", path)
        return CaptionResult(video_id, "error", original_language=original,
                             message=f"Could not save captions: {exc}")

    logger.info("Saved %s captions for %s -> %s", track["kind"], video_id, path)
    return CaptionResult(
        video_id, "ok",
        kind=track["kind"], language=lang, path=str(path),
        message=f"{track['kind']} · {lang} · {ext}",
        original_language=original,
    )


def download_captions(
    video_id: str,
    lang_code: str,
    output_dir: str,
    *,
    max_attempts: int | None = None,
    backoff_base: float | None = None,
    cancel_event=None,
    on_retry=None,
) -> CaptionResult:
    """Download captions with automatic retry + exponential backoff.

    Retries only transient failures (``_RETRYABLE``); permanent outcomes return
    immediately. Backoff waits are interruptible via ``cancel_event`` (a
    ``threading.Event``); if it is set the function returns a ``cancelled``
    result. ``on_retry(attempt, max_attempts, delay, status)`` is called before
    each backoff wait so the UI can show what's happening.
    """
    if max_attempts is None:
        max_attempts = settings.RETRY_MAX_ATTEMPTS
    if backoff_base is None:
        backoff_base = settings.RETRY_BACKOFF_BASE

    result = CaptionResult(video_id, "error", message="Not attempted.")
    for attempt in range(1, max_attempts + 1):
        if cancel_event is not None and cancel_event.is_set():
            return CaptionResult(video_id, "cancelled", message="Cancelled.", attempts=attempt - 1)

        result = fetch_video_captions(video_id, lang_code, output_dir)
        result.attempts = attempt

        if result.status == "ok" or result.status not in _RETRYABLE:
            return result

        if attempt < max_attempts:
            delay = backoff_base * (2 ** (attempt - 1))
            logger.info(
                "Retry %d/%d for %s in %.1fs (%s)",
                attempt, max_attempts - 1, video_id, delay, result.status,
            )
            if on_retry is not None:
                on_retry(attempt, max_attempts, delay, result.status)
            # Interruptible sleep: returns True if cancelled during the wait.
            if cancel_event is not None:
                if cancel_event.wait(delay):
                    return CaptionResult(video_id, "cancelled", message="Cancelled.", attempts=attempt)
            elif delay > 0:
                time.sleep(delay)

    logger.warning("Gave up on %s after %d attempts (%s)", video_id, max_attempts, result.status)
    return result
