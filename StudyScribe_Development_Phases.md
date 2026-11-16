# StudyScribe Development Phases

This document defines the planned implementation sequence for StudyScribe. Each phase should be completed, tested, and committed before work begins on the next phase.

---

## Phase 1 — GUI Shell

### Purpose

Build the initial StudyScribe desktop application interface using Python and CustomTkinter.

### What This Phase Provides

- Dark-themed main application window
- YouTube URL input field
- Output-folder selection control
- Export-format checkboxes
- Language selector
- Scrollable “Videos Found” area
- Progress bar
- Status label
- Start, Pause, and Cancel buttons

### Out of Scope

Do not implement:

- YouTube validation
- Playlist parsing
- Caption downloading
- Transcript cleanup
- File export logic
- Translation
- AI integration

### Acceptance Criteria

- Application starts without errors.
- Dark CustomTkinter main window opens.
- URL input field accepts text.
- Output-folder picker works.
- Export-option checkboxes work.
- Language selector defaults to English.
- Video list area is scrollable.
- Progress bar and status label display correctly.
- Start, Pause, and Cancel buttons exist.
- No YouTube, caption, export, or AI functions are implemented yet.

---

## Phase 2 — Validate Single YouTube URLs

### Purpose

Validate individual YouTube video URLs before any download or playlist processing occurs.

### What This Phase Provides

- Detection of valid YouTube video URLs
- Clear error messages for malformed URLs
- Handling for unsupported, private, unavailable, or invalid videos
- Basic metadata lookup for a valid single video, where supported

### Acceptance Criteria

- Valid YouTube video URLs are accepted.
- Invalid URLs produce user-friendly error messages.
- Unsupported URLs are rejected safely.
- Private or unavailable videos are reported clearly.
- Existing GUI behavior remains unchanged.

---

## Phase 3 — Read Playlist Metadata and Display Videos

### Purpose

Allow StudyScribe to detect playlists, retrieve playlist metadata, and display the included videos before processing begins.

### What This Phase Provides

- Playlist URL detection
- Playlist title retrieval
- Video title retrieval
- Video position and ordering
- Video duration display
- Per-video URL display or storage
- Caption-availability status
- Selectable video list for processing

### Acceptance Criteria

- A valid playlist URL is recognized.
- Playlist title and video count are displayed.
- Videos appear in playlist order.
- Each listed video includes title and duration.
- Caption availability is indicated when possible.
- User can select or deselect videos before processing.

---

## Phase 4 — Download Caption Tracks

### Purpose

Retrieve caption tracks for selected individual videos or playlist entries.

### What This Phase Provides

- Manual-caption retrieval
- Auto-generated-caption retrieval
- Caption language selection
- Raw transcript storage
- Per-video caption download status
- Graceful handling when captions are unavailable

### Acceptance Criteria

- Available captions can be downloaded for a selected video.
- Manual captions are preferred when available.
- Auto-generated captions are used when manual captions are unavailable.
- Raw transcript data is stored in a defined temporary or working location.
- Missing captions are reported without crashing the application.

---

## Phase 5 — Retry Logic and Progress Tracking

### Purpose

Improve reliability and user visibility during playlist processing.

### What This Phase Provides

- Automatic retry attempts for failed caption downloads
- Retry limits
- Skip-and-continue behavior after final failure
- Error logging
- Overall playlist progress
- Per-video progress and status
- Completed, failed, and remaining counts

### Acceptance Criteria

- Failed downloads are retried automatically.
- Retries stop after the configured maximum attempt count.
- Videos that still fail are marked and skipped.
- The playlist continues processing after individual failures.
- Progress bar and status text update during processing.
- Errors are written to structured logs.

---

## Phase 6 — Markdown Generation and File Naming

### Purpose

Convert downloaded transcripts into organized Markdown files.

### What This Phase Provides

- Clean Markdown transcript output
- Per-video metadata blocks
- Consistent headings
- Ordered filenames
- Playlist-specific output folders
- Sanitized filenames
- Optional README or index file generation

### Example Naming Format

```text
CCNP ENCOR/

01 - Introduction.md
02 - OSPF Fundamentals.md
03 - VLAN Review.md
04 - STP Deep Dive.md
...
27 - Final Review.md
```

### Acceptance Criteria

- Every completed video produces a Markdown file.
- Files are saved in the selected output folder.
- Filenames are safe for Windows, macOS, and Linux.
- Playlist order is preserved through numeric prefixes.
- Markdown includes title, duration, source URL, date, language, and caption type.
- File-generation errors are logged and shown clearly.

---

## Phase 7 — Speechify Cleanup Options

### Purpose

Make transcripts easier to listen to through Speechify or other text-to-speech tools.

### What This Phase Provides

- Optional timestamp removal
- Optional filler-word reduction
- Improved paragraph flow
- Long-paragraph splitting
- Preservation of CLI commands and code blocks
- Preservation of technical formatting
- Optional removal of repetitive intros, outros, and advertisements

### Acceptance Criteria

- User can enable or disable Speechify cleanup.
- CLI commands and code blocks remain unchanged.
- Long text sections are split into listener-friendly paragraphs.
- Timestamps are removed only when the option is enabled.
- Original/raw transcript remains available when appropriate.

---

## Phase 8 — PDF and DOCX Export

### Purpose

Export Markdown transcripts into polished, shareable documents.

### What This Phase Provides

- PDF export
- DOCX export
- Formatting for headings, body text, and code blocks
- Metadata preservation
- Readable page layout
- Output-folder integration

### Acceptance Criteria

- Selected Markdown files can export to PDF.
- Selected Markdown files can export to DOCX.
- Headings, code blocks, and metadata are preserved.
- Export failures are reported clearly.
- Markdown output remains the source-of-truth format.

---

## Phase 9 — Translation Support

### Purpose

Allow users to work with caption tracks in languages other than English.

### What This Phase Provides

- Output language selection
- Translation of supported caption tracks
- Original-language preservation
- Bilingual output option
- Clear labeling of source and translated content

### Acceptance Criteria

- User can select a target output language.
- When source captions are non-English, the program can generate a translated transcript when translation support is available.
- Users can choose original-only, translated-only, or bilingual output.
- Translation failures do not interrupt the rest of the playlist workflow.

---

## Phase 10 — AI Study-Guide Generation

### Purpose

Transform cleaned transcripts into structured study material.

### What This Phase Provides

- Learning objectives
- Clean study transcript
- Technical notes
- Cisco best practices
- Relevant RFC references
- Common mistakes
- Exam tips
- Real-world engineering considerations
- Key takeaways
- Flashcards
- Review questions

### Acceptance Criteria

- AI generation is optional and separate from caption downloading.
- Study-guide output is saved as Markdown first.
- Generated content uses clear section headings.
- Raw transcript and AI-enhanced study guide remain separate files.
- The system clearly identifies AI-generated content.
- Failures in AI processing do not corrupt the original transcript.

---

# Implementation Rules

- Implement one phase at a time.
- Do not begin later phases unless the current phase is working and tested.
- Do not refactor unrelated working modules without a clear technical reason.
- Keep GUI, services, utilities, configuration, and export logic separated.
- Use structured logging and meaningful error messages.
- Preserve raw captions before cleanup or transformation.
- Treat Markdown as the canonical source format for generated transcript content.
- Add or update tests as new functionality is introduced.

---

# Suggested Prompt for Claude in VS Code

```text
Read these project documents first:

- docs/StudyScribe_Master_Project_Specification.md
- docs/StudyScribe_Development_Phases.md

We are implementing Phase [NUMBER] only.

Do not begin later phases, add placeholder services, or modify unrelated files.

Before writing code:
1. Summarize the scope of this phase.
2. Identify the files that need to be created or changed.
3. List dependencies.
4. Define acceptance criteria and test steps.

After implementation:
1. Explain every changed file.
2. Provide steps to run and test the phase.
3. List known limitations.
```
