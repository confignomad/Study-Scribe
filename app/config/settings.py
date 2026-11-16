"""Application-wide configuration and defaults for StudyScribe.

Everything that other modules might want to tune (names, window size, export
formats, supported languages, log settings) lives here so there is a single
source of truth. Values are grouped on a frozen dataclass exposed as the
module-level singleton ``settings``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Project root = .../StudyScribe/  (this file is app/config/settings.py)
BASE_DIR: Path = Path(__file__).resolve().parents[2]
LOG_DIR: Path = BASE_DIR / "logs"


@dataclass(frozen=True)
class Settings:
    """Immutable container for StudyScribe defaults."""

    # --- Identity ---------------------------------------------------------
    APP_NAME: str = "StudyScribe"
    APP_VERSION: str = "0.1.0"

    # --- Paths ------------------------------------------------------------
    BASE_DIR: Path = BASE_DIR
    LOG_DIR: Path = LOG_DIR
    LOG_FILE: Path = LOG_DIR / "studyscribe.log"

    # --- Window / theme ---------------------------------------------------
    WINDOW_TITLE: str = "StudyScribe"
    WINDOW_WIDTH: int = 900
    WINDOW_HEIGHT: int = 720
    MIN_WIDTH: int = 760
    MIN_HEIGHT: int = 620
    APPEARANCE_MODE: str = "dark"          # dark theme requested for Phase 1
    COLOR_THEME: str = "blue"              # CustomTkinter built-in theme

    # --- Logging ----------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 1_000_000         # ~1 MB per file before rotating
    LOG_BACKUP_COUNT: int = 3

    # --- Network (Phase 2: URL validation) --------------------------------
    URL_CHECK_TIMEOUT: float = 10.0        # seconds before a lookup gives up
    USER_AGENT: str = f"StudyScribe/{APP_VERSION}"

    # --- Export formats (label shown next to each checkbox) ---------------
    EXPORT_FORMATS: tuple[str, ...] = (
        "Markdown",
        "PDF",
        "DOCX",
        "TXT",
        "HTML",
        "Speechify Formatting",
    )

    # --- Caption languages ------------------------------------------------
    LANGUAGES: tuple[str, ...] = (
        "English",
        "Spanish",
        "French",
        "German",
        "Portuguese",
        "Italian",
        "Japanese",
        "Korean",
        "Chinese",
    )
    DEFAULT_LANGUAGE: str = "English"

    # Map display language -> ISO code used by YouTube caption tracks.
    LANGUAGE_CODES: dict[str, str] = field(
        default_factory=lambda: {
            "English": "en",
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Portuguese": "pt",
            "Italian": "it",
            "Japanese": "ja",
            "Korean": "ko",
            "Chinese": "zh",
        }
    )

    # --- Caption download (Phase 4) ---------------------------------------
    RAW_SUBDIR: str = "raw_captions"  # under the user's output folder

    # --- Translation output mode (Phase 9) --------------------------------
    OUTPUT_MODES: tuple[str, ...] = ("Translated", "Original", "Bilingual")
    DEFAULT_OUTPUT_MODE: str = "Translated"

    # --- Retry / throttling (Phase 5) -------------------------------------
    RETRY_MAX_ATTEMPTS: int = 3        # total tries per video (1 + 2 retries)
    RETRY_BACKOFF_BASE: float = 2.0    # seconds; delay = base * 2**(attempt-1)
    DOWNLOAD_DELAY: float = 1.0        # polite pause between videos (seconds)


# Module-level singleton used throughout the app.
settings = Settings()
