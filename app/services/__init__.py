"""Service package.

Implemented:

* ``youtube.py``    - Phase 2: validate single YouTube video URLs + availability.
* ``playlist.py``   - Phase 3: enumerate playlist metadata + ordered video list.
* ``captions.py``   - Phase 4-5: download raw captions with retry.
* ``markdown_export.py`` - Phase 6: raw captions -> clean Markdown + file naming.
* ``transcript_format.py`` - Phase 7: paragraph reflow + Speechify cleanup.
* ``exporter.py``   - Phase 8: export Markdown transcript to PDF/DOCX/TXT/HTML.
* ``captions.py``   - Phase 9 adds translation via YouTube (target/original/bilingual).
* ``study_guide.py`` - Phase 10: paste-ready AI study-guide prompt-pack.
"""

from app.services.study_guide import (
    build_study_guide_prompt,
    write_study_guide_prompt,
)
from app.services.markdown_export import (
    build_bilingual_body,
    build_markdown,
    sanitize_filename,
    vtt_to_text,
    write_playlist_index,
    write_video_markdown,
)
from app.services.transcript_format import (
    paragraphize,
    remove_fillers,
    speechify_clean,
    split_sentences,
    trim_intro_outro,
)
from app.services.captions import (
    ORIGINAL_LANG,
    CaptionResult,
    detect_original_language,
    download_captions,
    fetch_video_captions,
    select_caption_track,
)
from app.services.playlist import (
    Playlist,
    PlaylistEntry,
    entries_from_info,
    fetch_playlist,
    format_duration,
)
from app.services.youtube import (
    ParsedURL,
    VideoValidation,
    check_video_availability,
    parse_youtube_url,
    validate_single_video,
)

__all__ = [
    "ParsedURL",
    "VideoValidation",
    "check_video_availability",
    "parse_youtube_url",
    "validate_single_video",
    "Playlist",
    "PlaylistEntry",
    "entries_from_info",
    "fetch_playlist",
    "format_duration",
    "CaptionResult",
    "ORIGINAL_LANG",
    "detect_original_language",
    "download_captions",
    "fetch_video_captions",
    "select_caption_track",
    "build_bilingual_body",
    "build_markdown",
    "sanitize_filename",
    "vtt_to_text",
    "write_playlist_index",
    "write_video_markdown",
    "paragraphize",
    "remove_fillers",
    "speechify_clean",
    "split_sentences",
    "trim_intro_outro",
    "build_study_guide_prompt",
    "write_study_guide_prompt",
]
