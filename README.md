# StudyScribe

StudyScribe is a Python desktop application that (eventually) downloads captions
from YouTube videos and playlists, organizes them into Markdown files, and
exports them into study-friendly formats (PDF, DOCX, TXT, HTML, and a
Speechify-friendly layout).

## Application Screenshot

![StudyScribe Application](docs/your-screenshot.png)


> **Current status — Phases 1 & 2 complete.**
> The dark-themed [CustomTkinter](https://customtkinter.tomschimansky.com/) shell
> is built (Phase 1), and **Start** now validates a single YouTube video URL and
> confirms the video exists via YouTube's oEmbed endpoint, showing its title and
> channel (Phase 2). Playlist enumeration, caption downloading, and export logic
> are **not implemented yet** — see the [Roadmap](#roadmap).

---

## Requirements

- **Python 3.13+**
- Dependencies listed in [requirements.txt](requirements.txt)

## Installation

```bash
# From the StudyScribe/ directory
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## Running

```bash
python main.py
```

---

## Project structure

```
StudyScribe/
├── main.py               # Entry point: sets up logging + launches the GUI
├── requirements.txt      # Runtime dependencies
├── README.md             # This file
├── app/
│   ├── __init__.py       # Marks `app` as a package; exposes version
│   ├── gui/
│   │   ├── __init__.py
│   │   └── main_window.py   # The CustomTkinter main window (all widgets)
│   ├── services/
│   │   ├── __init__.py
│   │   └── youtube.py       # Phase 2: URL validation + availability lookup
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py        # Central logging configuration
│   └── config/
│       ├── __init__.py
│       └── settings.py      # App-wide constants & defaults
├── tests/                   # Unit tests (run: python -m unittest discover -s tests)
│   ├── __init__.py
│   └── test_youtube.py
└── logs/                    # Rotating log files are written here at runtime
```

### What each part is responsible for

| Location                  | Responsibility                                                        |
|---------------------------|-----------------------------------------------------------------------|
| `main.py`                 | Process entry point, top-level exception guard, launches the window.  |
| `app/config/settings.py`  | Single source of truth for names, defaults, sizes, export formats.    |
| `app/utils/logger.py`     | Configures console + rotating-file logging; `get_logger()` helper.    |
| `app/gui/main_window.py`  | Builds the dark-themed UI; runs URL validation on a background thread. |
| `app/services/youtube.py` | Validates YouTube URLs and checks video availability (Phase 2).       |
| `tests/`                  | Unit tests for the service layer (offline; network is stubbed).       |
| `logs/`                   | Runtime log output (`studyscribe.log`).                               |

---

## Roadmap

Authoritative plan lives in
[StudyScribe_Development_Phases.md](StudyScribe_Development_Phases.md) and
[StudyScribe_Master_Project_Specification.md](StudyScribe_Master_Project_Specification.md).

- ✅ **Phase 1 — GUI Shell:** dark CustomTkinter window with all controls.
- ✅ **Phase 2 — Validate Single URLs:** URL parsing + availability lookup.
- **Phase 3 — Playlist Metadata:** detect playlists; list videos (title, order, duration, caption availability) as a selectable list.
- **Phase 4 — Download Caption Tracks:** manual/auto captions; store raw transcripts.
- **Phase 5 — Retry Logic & Progress Tracking:** auto-retry, skip-and-continue, live progress.
- **Phase 6 — Markdown Generation & File Naming:** ordered, sanitized files with metadata.
- **Phase 7 — Speechify Cleanup:** timestamp/filler removal, paragraph flow (preserve code/CLI).
- **Phase 8 — PDF & DOCX Export:** polished documents; Markdown stays source-of-truth.
- **Phase 9 — Translation Support:** target-language output; original / translated / bilingual.
- **Phase 10 — AI Study-Guide Generation:** objectives, notes, flashcards, exam tips.
