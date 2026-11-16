"""YouTube URL validation service (Phase 2).

This module is intentionally free of any GUI code. Every function returns plain
data (dataclasses / dicts), so the logic can be unit-tested without launching a
window — following the project rule that logic stays separated from the UI.

Phase 2 scope:

* ``parse_youtube_url``        - pure, offline URL parsing + video-ID extraction.
* ``check_video_availability`` - lightweight network liveness check via YouTube's
                                 public oEmbed endpoint (no third-party deps).
* ``validate_single_video``    - combines the two into one user-facing result.

Playlist handling, caption downloading, and metadata beyond title/author are
deliberately out of scope until later phases.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- YouTube host / ID recognition ------------------------------------------
_MAIN_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_YOUTUBE_HOSTS = _MAIN_HOSTS | _SHORT_HOSTS

# YouTube video IDs are exactly 11 chars from this alphabet.
import re  # noqa: E402  (kept next to the pattern it powers)

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

_OEMBED_ENDPOINT = "https://www.youtube.com/oembed"


@dataclass
class ParsedURL:
    """Result of offline URL parsing.

    ``kind`` is one of ``"video"``, ``"playlist"``, or ``"invalid"``.
    """

    kind: str
    video_id: str | None = None
    playlist_id: str | None = None
    canonical_url: str | None = None
    reason: str = ""  # human-readable explanation when kind == "invalid"


@dataclass
class VideoValidation:
    """User-facing outcome of validating a single video URL."""

    ok: bool
    url: str
    status: str  # ok | invalid | playlist | private | unavailable | network_error | error
    message: str
    video_id: str | None = None
    title: str | None = None
    author: str | None = None


def parse_youtube_url(url: str) -> ParsedURL:
    """Parse ``url`` offline and classify it. Performs no network access.

    Accepts the common single-video forms (watch, youtu.be, shorts, embed, /v/,
    live) with or without a scheme, and recognizes playlist URLs. A video URL
    that also carries a ``list=`` parameter is still treated as a video (we can
    validate the specific video); the playlist ID is preserved for later phases.
    """
    if not url or not url.strip():
        return ParsedURL("invalid", reason="No URL provided.")

    raw = url.strip()
    if not _SCHEME_RE.match(raw):
        # Users routinely paste "youtu.be/…" without a scheme.
        raw = "https://" + raw

    try:
        parsed = urlparse(raw)
    except ValueError:
        return ParsedURL("invalid", reason="Could not parse that URL.")

    host = (parsed.hostname or "").lower()
    if host not in _YOUTUBE_HOSTS:
        return ParsedURL("invalid", reason="This is not a YouTube URL.")

    path = parsed.path or ""
    query = parse_qs(parsed.query or "")
    playlist_id = query.get("list", [None])[0]

    video_id: str | None = None
    if host in _SHORT_HOSTS:
        video_id = path.lstrip("/").split("/")[0] or None
    else:
        segments = [seg for seg in path.split("/") if seg]
        if path.rstrip("/") == "/watch":
            video_id = query.get("v", [None])[0]
        elif segments and segments[0] in ("shorts", "embed", "v", "live"):
            video_id = segments[1] if len(segments) > 1 else None
        # "/playlist" (and anything else) leaves video_id as None.

    if video_id is not None:
        if _VIDEO_ID_RE.match(video_id):
            return ParsedURL(
                "video",
                video_id=video_id,
                playlist_id=playlist_id,
                canonical_url=f"https://www.youtube.com/watch?v={video_id}",
            )
        return ParsedURL(
            "invalid",
            reason="That looks like a YouTube link, but the video ID is malformed.",
        )

    if playlist_id:
        return ParsedURL("playlist", playlist_id=playlist_id)

    return ParsedURL(
        "invalid",
        reason="Couldn't find a video ID in that YouTube URL.",
    )


def check_video_availability(
    video_id: str,
    timeout: float | None = None,
) -> dict:
    """Confirm a video exists and fetch basic metadata via the oEmbed endpoint.

    Returns a dict with a ``status`` key:

    * ``"ok"``            - includes ``title`` and ``author``.
    * ``"private"``       - HTTP 401 (private or embedding disabled).
    * ``"unavailable"``   - HTTP 404 (removed / never existed).
    * ``"network_error"`` - could not reach YouTube (offline, timeout, DNS).
    * ``"error"``         - unexpected HTTP status or malformed response.

    This is the only function here that touches the network.
    """
    if timeout is None:
        timeout = settings.URL_CHECK_TIMEOUT

    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    endpoint = f"{_OEMBED_ENDPOINT}?{urlencode({'url': watch_url, 'format': 'json'})}"
    request = Request(endpoint, headers={"User-Agent": settings.USER_AGENT})

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "status": "ok",
            "title": payload.get("title"),
            "author": payload.get("author_name"),
        }
    except HTTPError as exc:
        if exc.code == 401:
            return {"status": "private", "message": "This video is private or does not allow external lookups."}
        if exc.code in (400, 404):
            # 404 = removed; 400 = YouTube rejects the (nonexistent) video reference.
            return {"status": "unavailable", "message": "This video is unavailable or has been removed."}
        logger.warning("oEmbed returned HTTP %s for video %s", exc.code, video_id)
        return {"status": "error", "message": f"Unexpected response from YouTube (HTTP {exc.code})."}
    except (URLError, socket.timeout, TimeoutError) as exc:
        logger.warning("Network error checking video %s: %s", video_id, exc)
        return {"status": "network_error", "message": "Could not reach YouTube. Check your internet connection."}
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Malformed oEmbed response for video %s: %s", video_id, exc)
        return {"status": "error", "message": "Received an unreadable response from YouTube."}


def validate_single_video(url: str, timeout: float | None = None) -> VideoValidation:
    """Validate a single YouTube video URL end to end.

    Parses the URL offline first, then (only for well-formed video URLs) performs
    the network availability check. Playlist URLs are rejected with a Phase-3
    pointer so single-video validation stays focused.
    """
    parsed = parse_youtube_url(url)

    if parsed.kind == "invalid":
        return VideoValidation(ok=False, url=url, status="invalid", message=parsed.reason)

    if parsed.kind == "playlist":
        return VideoValidation(
            ok=False,
            url=url,
            status="playlist",
            message="That's a playlist URL — playlist support arrives in Phase 3. "
            "Paste a single video URL for now.",
        )

    # kind == "video"
    availability = check_video_availability(parsed.video_id, timeout=timeout)
    status = availability["status"]

    if status == "ok":
        title = availability.get("title") or "(untitled)"
        return VideoValidation(
            ok=True,
            url=parsed.canonical_url or url,
            status="ok",
            message=f"Valid video: {title}",
            video_id=parsed.video_id,
            title=title,
            author=availability.get("author"),
        )

    return VideoValidation(
        ok=False,
        url=parsed.canonical_url or url,
        status=status,
        message=availability.get("message", "Could not validate this video."),
        video_id=parsed.video_id,
    )
