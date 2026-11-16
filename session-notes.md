# StudyScribe — Session Notes

Summary of the build session that took StudyScribe from an empty idea to a
feature-complete app across all 10 planned phases.

## What StudyScribe is
A Python 3.13 + CustomTkinter (dark theme) desktop app that turns YouTube
videos/playlists into study materials:

> paste a video/playlist URL → validate → list & select videos → download
> captions (retry/throttle, pause/cancel) → translate (target/original/
> bilingual) → clean Markdown with metadata → Speechify variant → export
> PDF/DOCX/TXT/HTML → paste-ready AI study-guide prompt.

Built strictly one phase at a time per `StudyScribe_Development_Phases.md` and
`StudyScribe_Master_Project_Specification.md`.

## Phases completed this session
1. **GUI Shell** — dark CustomTkinter window; all controls laid out.
2. **Validate Single URLs** — stdlib URL parsing + YouTube oEmbed liveness
   check (no dependency); background thread keeps the UI responsive.
3. **Playlist Metadata** — yt-dlp flat enumeration; selectable checklist with
   title/duration; "Select all / None". (verified on a real 27-video playlist)
4. **Download Caption Tracks** — yt-dlp; manual preferred over auto; raw `.vtt`
   preserved under `<output>/<playlist>/raw_captions/`; stateful Start button
   ("Start" → "Download Captions").
5. **Retry + Progress** — exponential backoff for transient failures (429 /
   network), fast-fail on permanent ones; 1s polite delay between videos to
   avoid 429; determinate progress + ok/failed/remaining counts; real
   Pause/Resume and Cancel (interruptible via threading.Event).
6. **Markdown Generation** — VTT → clean text (strips headers/timings/inline
   tags, de-dups rolling auto-caption lines); metadata header; sanitized
   ordered names `NN - Title.md`; per-playlist folder + README index.
7. **Speechify Cleanup** — sentence→paragraph reflow (applied to the standard
   `.md` for readability); optional `(Speechify).md` variant (filler/intro/
   outro trim); fenced code blocks preserved.
8. **PDF / DOCX / TXT / HTML Export** — reportlab (PDF), python-docx (DOCX),
   hand-rolled TXT/HTML; driven by the format checkboxes; per-format failures
   isolated.
9. **Translation** — YouTube auto-translation (no new dep); Target-language
   dropdown + Output mode (Translated / Original / Bilingual); original-language
   detection; bilingual documents; translation labels in metadata.
10. **AI Study-Guide Prompt** — opt-in "AI study-guide prompt" checkbox writes
    a paste-ready `(Study Guide Prompt).md` (all spec sections + transcript) to
    drop into Claude/ChatGPT/Gemini. No API key, no cost (user's choice over a
    direct Claude API integration).

## Key decisions
- **No API keys / paid services by default** — validation via oEmbed, playlist
  + captions + translation via yt-dlp/YouTube, AI step as a paste-ready prompt.
- **yt-dlp** is the engine for playlist enumeration, caption download, and
  (via YouTube auto-translate) translation.
- **Config stays a frozen dataclass** in `app/config/settings.py` (JSON
  persistence deferred until a settings window needs it).
- **All `.md`/`.txt` output is UTF-8 with a BOM** — the user views files in
  **Sublime Text**, which defaults to Windows-1252 and needs the BOM to detect
  UTF-8 (this fixed the `für`→`fÃ¼r` mojibake, which was always a viewer issue,
  never file corruption).
- **Tests are stdlib `unittest`, fully offline** (network stubbed): 70 passing.

## Dependencies (final)
`customtkinter`, `yt-dlp`, `reportlab`, `python-docx`. Everything else is
Python stdlib.

## Project layout (added this session)
```
app/services/
  youtube.py          # Phase 2: URL validation + availability
  playlist.py         # Phase 3: playlist enumeration
  captions.py         # Phase 4-5,9: download + retry + original-lang detection
  markdown_export.py  # Phase 6: VTT->Markdown, naming, bilingual body
  transcript_format.py# Phase 7: paragraph reflow + Speechify cleanup
  exporter.py         # Phase 8: PDF/DOCX/TXT/HTML
  study_guide.py      # Phase 10: AI study-guide prompt-pack
tests/                # test_youtube, _playlist, _captions, _retry, _markdown,
                      #   _transcript_format, _exporter, _translation, _study_guide
```

## Target language vs Output mode (clarified)
- **Target language** = the language you want the transcript in (YouTube can
  auto-translate to it).
- **Output mode** matters only when the video's spoken language differs from
  the target: **Translated** = target only; **Original** = spoken language only;
  **Bilingual** = both in one file.
- For an **English video with target English**, all three collapse to the same
  English transcript — pick **Translated** (the default).

## Verified
- Live: 27-video playlist enumerated with durations; captions downloaded 27/27;
  English + German caption downloads; en→es bilingual via YouTube translation;
  all four export formats with valid signatures; study-guide prompt generated.
- 70 unit tests passing.

## Not done / possible follow-ups
- Refresh `README.md` for all 10 phases + final deps + new controls.
- Pin `requirements.txt` versions.
- Optional project permission allowlist so routine python/test commands don't
  prompt.
- Full-app GUI smoke run with multiple checkboxes on.

## Note (environment)
The Claude API workspace powering the Code session hit its **monthly spend
limit** (resets 2026-08-01 UTC). Unrelated to StudyScribe; fix via Anthropic
Console → Settings → Workspaces → Spend limits, or switch workspaces.
