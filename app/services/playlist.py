"""YouTube playlist enumeration service (Phase 3).

Reads a playlist's metadata and its ordered list of videos using yt-dlp in
*flat* mode — a single fast network call that returns each video's id, title,
position, and (usually) duration without visiting every video page.

Per the Phase 3 decision, per-video **caption availability is deferred** to
Phase 4: entries carry ``caption_status = "unknown"`` for now.

As with the rest of the service layer, this module contains no GUI code. The
pure transform (``entries_from_info``) and ``format_duration`` are unit-tested
offline; only ``fetch_playlist`` touches the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PlaylistEntry:
    """A single video within a playlist."""

    position: int
    video_id: str
    title: str
    url: str
    duration: int | None = None      # seconds, or None if unknown
    caption_status: str = "unknown"  # resolved in Phase 4


@dataclass
class Playlist:
    """Result of reading a playlist."""

    ok: bool
    playlist_id: str | None
    title: str
    entries: list[PlaylistEntry] = field(default_factory=list)
    status: str = "ok"  # ok | empty | error
    message: str = ""


def format_duration(seconds: int | float | None) -> str:
    """Format a duration in seconds as ``M:SS`` or ``H:MM:SS`` (``—`` if unknown)."""
    if seconds is None:
        return "—"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def entries_from_info(info: dict) -> list[PlaylistEntry]:
    """Pure transform: yt-dlp flat playlist info dict -> ordered PlaylistEntry list.

    Skips empty/unavailable entries (yt-dlp yields ``None`` for those) while
    keeping the 1-based position numbering aligned to the surviving videos.
    """
    entries: list[PlaylistEntry] = []
    position = 0
    for raw in info.get("entries") or []:
        if not raw:
            continue
        video_id = raw.get("id") or ""
        if not video_id:
            continue
        position += 1
        title = raw.get("title") or "(untitled)"
        url = raw.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        entries.append(
            PlaylistEntry(
                position=position,
                video_id=video_id,
                title=title,
                url=url,
                duration=raw.get("duration"),
            )
        )
    return entries


def fetch_playlist(url_or_id: str, timeout: float | None = None) -> Playlist:
    """Enumerate a playlist via yt-dlp flat extraction (network).

    ``url_or_id`` may be a full playlist URL or a bare playlist ID. Returns a
    :class:`Playlist`; on any failure ``ok`` is False with a user-friendly
    ``message`` (private, unavailable, empty, or network problems).
    """
    if timeout is None:
        timeout = settings.URL_CHECK_TIMEOUT

    url = url_or_id.strip()
    if url and not url.lower().startswith("http"):
        url = f"https://www.youtube.com/playlist?list={url}"

    # Imported lazily so the rest of the app (and the offline tests) don't
    # require yt-dlp to be installed.
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "socket_timeout": timeout,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.warning("Playlist extraction failed for %r: %s", url, exc)
        return Playlist(
            ok=False,
            playlist_id=None,
            title="",
            status="error",
            message="Could not read this playlist. It may be private, unavailable, "
            "or the connection failed.",
        )
    except Exception as exc:  # noqa: BLE001 - never let an unexpected error escape
        logger.exception("Unexpected error reading playlist %r", url)
        return Playlist(
            ok=False,
            playlist_id=None,
            title="",
            status="error",
            message=f"Unexpected error reading playlist: {exc}",
        )

    if not info:
        return Playlist(
            ok=False, playlist_id=None, title="", status="error",
            message="No data returned for that playlist.",
        )

    title = info.get("title") or "Playlist"
    playlist_id = info.get("id")
    entries = entries_from_info(info)

    if not entries:
        return Playlist(
            ok=False, playlist_id=playlist_id, title=title, status="empty",
            message="This playlist has no available videos.",
        )

    return Playlist(
        ok=True,
        playlist_id=playlist_id,
        title=title,
        entries=entries,
        status="ok",
        message=f"{title} — {len(entries)} videos",
    )
