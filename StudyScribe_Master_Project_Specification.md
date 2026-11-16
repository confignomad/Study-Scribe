# Project Specification – StudyScribe

## Project Overview

**StudyScribe** is a modern desktop application designed to automatically convert YouTube videos or entire playlists into professionally organized study materials.

Rather than producing raw transcripts, StudyScribe downloads available caption tracks, cleans and organizes the content, and exports it into multiple formats optimized for reading, listening with text-to-speech applications such as Speechify, or importing into AI assistants for advanced study guide generation.

The application is intended for students, educators, IT professionals, certification candidates, researchers, and lifelong learners.

---

# Primary Goals

The application should:

- Download captions from individual YouTube videos or entire playlists.
- Support both manually created and auto-generated captions.
- Automatically organize downloaded transcripts.
- Produce clean, well-structured Markdown files.
- Export transcripts into multiple document formats.
- Prepare transcripts for AI processing and Speechify narration.
- Automate repetitive tasks while maintaining a professional workflow.

---

# Core Workflow

```text
YouTube URL
        │
        ▼
Validate URL
        │
        ▼
Read Playlist
        │
        ▼
Retrieve Captions
        │
        ▼
Retry Missing Downloads
        │
        ▼
Clean and Normalize Transcript
        │
        ▼
Save as Markdown
        │
        ▼
(Optional)
Export PDF
Export DOCX
Export TXT
Export HTML
        │
        ▼
Import into ChatGPT, Claude, Gemini, or another AI
        │
        ▼
Generate Professional Study Guide
```

---

# Core Features

## Playlist Support

The application should accept either:

- A single YouTube video URL
- A complete YouTube playlist URL

When a playlist is supplied, the application should automatically:

- Read every video in the playlist
- Display the title of each video
- Display video duration
- Detect caption availability
- Display download status
- Process every video sequentially

---

## Caption Download

Support:

- Manual captions
- Auto-generated captions
- Multiple languages

If English captions are unavailable, the application should attempt to retrieve translated captions when supported.

---

## Automatic Retry

If caption retrieval fails:

```text
Attempt 1

↓

Attempt 2

↓

Attempt 3

↓

Skip Video

↓

Continue Playlist
```

No manual intervention should be required.

---

## Progress Monitoring

Display a modern progress interface showing:

- Overall playlist progress
- Current video
- Videos completed
- Videos remaining
- Estimated remaining time
- Download speed (optional)

Example:

```text
Playlist Progress

██████████░░░░░░░░░░

12 / 27 Videos

44%

Current Video

OSPF LSA Types

Estimated Time Remaining:
18 minutes
```

---

## Automatic File Naming

Automatically create organized folders.

Example:

```text
CCNP ENCOR/

01 - Introduction.md

02 - OSPF Fundamentals.md

03 - VLAN Review.md

04 - STP Deep Dive.md

...

27 - Final Review.md
```

The application should automatically sanitize filenames by removing invalid characters.

---

## Markdown Output

Each transcript should begin with metadata.

Example:

```markdown
# OSPF Fundamentals

Length: 9:47

Source:
https://youtube.com/...

Downloaded:
2026-06-29

Language:
English

Caption Type:
Auto Generated
```

Markdown was chosen because it imports cleanly into:

- Obsidian
- Notion
- GitHub
- ChatGPT
- Claude
- VS Code
- Cursor
- Visual Studio Code

---

## Export Formats

Provide optional exports to:

- Markdown (.md)
- PDF
- DOCX
- TXT
- HTML

Future enhancement:

- EPUB

---

## Translation Support

If only foreign-language captions exist:

```text
Spanish Captions

↓

Translate to English

↓

Save English Transcript
```

Optionally preserve both:

- Original language
- English translation

---

# User Interface

Use **CustomTkinter** to create a modern dark-themed interface.

Main Window:

```text
--------------------------------------------------
                StudyScribe
--------------------------------------------------

YouTube URL

[________________________________________]

Browse Output Folder

[ Select Folder ]

--------------------------------------------

Output Formats

☑ Markdown

☑ PDF

☑ DOCX

☑ TXT

☑ HTML

☑ Speechify Formatting

--------------------------------------------

Language

English ▼

--------------------------------------------

Videos Found

☑ Video 1

☑ Video 2

☑ Video 3

☑ Video 4

...

--------------------------------------------

███████████████░░░░░░░░

13 / 27 Complete

--------------------------------------------

Start

Pause

Cancel
```

---

# Advanced Options

Create a dedicated Settings window containing options such as:

- Remove timestamps
- Remove filler words
- Preserve speaker names
- Preserve code blocks
- Preserve CLI commands
- Merge short paragraphs
- Split long paragraphs
- Optimize formatting for Speechify
- Generate chapter headings
- Remove advertisements
- Skip introductions
- Skip outros
- Download video thumbnails
- Save playlist metadata
- Automatically organize folders
- Automatically create README files

---

# AI Integration

Once transcripts have been downloaded, provide an option to prepare them for AI-assisted study guide generation.

Each transcript should be optimized for transformation into a professional study guide containing:

- Video Information
- Learning Objectives
- Clean Study Transcript
- Technical Notes
- Cisco Best Practices
- Relevant RFC References
- Common Mistakes
- Exam Tips
- Real-World Engineering Considerations
- Key Takeaways
- Flashcards
- Review Questions

The resulting documents should be optimized for:

- Reading
- Listening with Speechify
- AI summarization
- Long-term reference
- Certification exam preparation

---

# Long-Term Vision

StudyScribe should evolve into a complete learning platform consisting of three primary components.

## StudyScribe Downloader

- Downloads captions
- Organizes playlists
- Exports transcripts
- Supports multiple languages
- Provides document conversion

## StudyScribe AI

Uses AI to transform transcripts into professionally written study guides.

Possible outputs include:

- Structured lessons
- Technical explanations
- Flashcards
- Practice quizzes
- Executive summaries
- RFC references
- Cisco best practices
- Real-world deployment notes
- Exam preparation material

## StudyScribe Library

A searchable knowledge base for all generated content.

Features may include:

- Full-text search
- Folder organization
- Tagging
- Categories
- Favorites
- Reading history
- AI-assisted search
- Speechify integration
- Cloud synchronization (future enhancement)

---

# Technical Requirements

- Language: Python 3.13+
- GUI Framework: CustomTkinter
- Modular architecture
- Object-oriented design
- Multithreaded downloads to keep the UI responsive
- Structured logging
- Configuration stored in JSON
- Automatic update checker (future enhancement)
- Cross-platform support for Windows, macOS, and Linux
- Comprehensive error handling and recovery

---

# Development Phases

## Phase 1 — GUI Shell

Build the main StudyScribe window: URL field, output-folder picker, format checkboxes, language selector, video list area, progress bar, and Start, Pause, and Cancel controls. No downloading logic is required yet.

## Phase 2 — Validate Single YouTube URLs

Check that a pasted URL is a valid YouTube video link and provide clear errors for invalid, private, unavailable, or unsupported URLs.

## Phase 3 — Read Playlist Metadata and Display Videos

Detect playlist links, read playlist metadata, and display each video's title, position, duration, URL, and caption availability before processing begins.

## Phase 4 — Download Caption Tracks

Retrieve available manual or auto-generated captions and save the raw transcript data for each selected video.

## Phase 5 — Retry Logic and Progress Tracking

Add automatic retries for failed caption downloads, skip videos that still fail, log errors, and update the progress bar, status text, and completion count.

## Phase 6 — Markdown Generation and File Naming

Convert downloaded captions into clean Markdown files with consistent metadata, sanitized filenames, playlist folders, and ordered names such as `01 - OSPF Fundamentals.md`.

## Phase 7 — Speechify Cleanup Options

Clean transcripts for text-to-speech by removing timestamps and filler words, improving paragraph flow, preserving CLI and code blocks, and breaking up long sections for easier listening.

## Phase 8 — PDF and DOCX Export

Convert Markdown transcripts into polished PDF and Microsoft Word documents while retaining headings, code blocks, metadata, and readable formatting.

## Phase 9 — Translation Support

Allow the user to select an output language. If captions are only available in another language, the program can translate them to English or save both original and translated versions.

## Phase 10 — AI Study-Guide Generation

Send cleaned transcripts through an AI workflow to generate learning objectives, technical notes, RFC references, Cisco best practices, flashcards, key takeaways, exam tips, and review questions.

---

# Design Philosophy

StudyScribe should provide a clean, professional, and intuitive user experience. The workflow should minimize manual effort while producing organized, high-quality transcripts that are immediately usable for AI-assisted learning, technical documentation, certification preparation, and text-to-speech narration.

The application should emphasize automation, consistency, reliability, and extensibility, allowing it to grow into a complete study ecosystem rather than simply a transcript downloader.
