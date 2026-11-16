"""StudyScribe application entry point.

Bootstraps logging, loads configuration, and launches the CustomTkinter GUI.
Run with:  python main.py
"""

import sys

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    """Start the StudyScribe desktop application.

    Returns a process exit code (0 = clean shutdown, 1 = fatal error).
    """
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    try:
        # Imported lazily so a missing GUI dependency produces a clear log
        # message instead of failing at module import time.
        from app.gui.main_window import MainWindow

        app = MainWindow()
        app.mainloop()
    except ImportError as exc:
        logger.critical(
            "A required dependency is missing (%s). "
            "Install requirements with: pip install -r requirements.txt",
            exc,
        )
        return 1
    except Exception:  # noqa: BLE001 - top-level guard, we want everything logged
        logger.exception("Unhandled exception; StudyScribe is shutting down.")
        return 1

    logger.info("%s closed normally.", settings.APP_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
