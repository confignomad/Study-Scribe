"""StudyScribe main window.

Dark-themed CustomTkinter GUI. Implemented through Phase 4:

* Phase 1 - layout: URL field, output folder, format checkboxes, language menu,
  scrollable "Videos Found", Start/Pause/Cancel, progress bar, status label.
* Phase 2 - Start validates a single video URL (title/channel via oEmbed).
* Phase 3 - Start enumerates a playlist into a selectable checklist.
* Phase 4 - after discovery, Start becomes "Download Captions" and downloads
  raw caption tracks for the selected videos, showing per-video status.

Network work runs on background threads; results are marshalled back onto the
Tk main thread via ``self.after``.
"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.config.settings import settings
from app.services.captions import ORIGINAL_LANG, CaptionResult, download_captions
from app.services.exporter import EXPORT_LABELS, export_video
from app.services.markdown_export import (
    build_bilingual_body,
    sanitize_filename,
    write_playlist_index,
    write_video_markdown,
)
from app.services.playlist import (
    Playlist,
    PlaylistEntry,
    fetch_playlist,
    format_duration,
)
from app.services.study_guide import write_study_guide_prompt
from app.services.youtube import (
    VideoValidation,
    parse_youtube_url,
    validate_single_video,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Status-label colors keyed by message level -> (light_mode, dark_mode).
_STATUS_COLORS: dict[str, tuple[str, str]] = {
    "info": ("gray50", "gray65"),
    "success": ("#2e7d32", "#66bb6a"),
    "error": ("#c62828", "#ef5350"),
}


class MainWindow(ctk.CTk):
    """The StudyScribe application's main window."""

    def __init__(self) -> None:
        super().__init__()

        # --- Theme / appearance ------------------------------------------
        ctk.set_appearance_mode(settings.APPEARANCE_MODE)
        ctk.set_default_color_theme(settings.COLOR_THEME)

        # --- Window setup ------------------------------------------------
        self.title(settings.WINDOW_TITLE)
        self.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.minsize(settings.MIN_WIDTH, settings.MIN_HEIGHT)

        # --- State holders (bound to widgets) ----------------------------
        self.url_var = ctk.StringVar()
        self.output_dir_var = ctk.StringVar(value="")
        self.language_var = ctk.StringVar(value=settings.DEFAULT_LANGUAGE)
        self.output_mode_var = ctk.StringVar(value=settings.DEFAULT_OUTPUT_MODE)
        self.study_guide_var = ctk.BooleanVar(value=False)  # Phase 10 (opt-in)
        self.status_var = ctk.StringVar(value="Ready.")
        # Reverse map (ISO code -> display name) for translation labels.
        self._code_to_lang = {code: name for name, code in settings.LANGUAGE_CODES.items()}
        # One BooleanVar per export format, keyed by its label.
        self.format_vars: dict[str, ctk.BooleanVar] = {
            fmt: ctk.BooleanVar(value=(fmt == "Markdown"))
            for fmt in settings.EXPORT_FORMATS
        }

        # Discovery / download state (Phases 3-5).
        self._mode = "idle"            # "idle" -> discover ; "discovered" -> download
        self._discovered_url = ""
        self._targets: list[PlaylistEntry] = []
        self._playlist_title: str | None = None  # None => single video
        self.selection_vars: dict[str, ctk.BooleanVar] = {}
        self.row_status: dict[str, ctk.CTkLabel] = {}
        # Download control (Phase 5).
        self._downloading = False
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()  # set == paused
        # Revert to discover-mode if the user edits the URL after discovery.
        self.url_var.trace_add("write", self._on_url_changed)

        # Make the "Videos Found" row the one that stretches vertically.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._build_header()
        self._build_input_section()
        self._build_options_section()
        self._build_videos_section()
        self._build_controls_section()
        self._build_status_section()

        logger.info("Main window initialized.")

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_header(self) -> None:
        """App title banner at the top."""
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=settings.APP_NAME,
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(14, 0))

        ctk.CTkLabel(
            header,
            text="Download & organize YouTube captions into study-ready notes",
            font=ctk.CTkFont(size=13),
            text_color=("gray60", "gray70"),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

    def _build_input_section(self) -> None:
        """YouTube URL entry + output-folder selector."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        frame.grid_columnconfigure(1, weight=1)

        # --- YouTube URL ---
        ctk.CTkLabel(frame, text="YouTube URL:").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=12
        )
        self.url_entry = ctk.CTkEntry(
            frame,
            textvariable=self.url_var,
            placeholder_text="Paste a video or playlist URL…",
        )
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)

        # --- Output folder ---
        ctk.CTkLabel(frame, text="Output folder:").grid(
            row=1, column=0, sticky="w", padx=(16, 8), pady=(0, 12)
        )
        self.output_entry = ctk.CTkEntry(
            frame,
            textvariable=self.output_dir_var,
            placeholder_text="No folder selected…",
        )
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 12))

        self.browse_button = ctk.CTkButton(
            frame,
            text="Select Folder",
            width=120,
            command=self._on_select_output_folder,
        )
        self.browse_button.grid(row=1, column=2, padx=(0, 16), pady=(0, 12))

    def _build_options_section(self) -> None:
        """Export-format checkboxes + language dropdown."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        frame.grid_columnconfigure(0, weight=1)

        # --- Export formats ---
        ctk.CTkLabel(
            frame,
            text="Export formats:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        checks = ctk.CTkFrame(frame, fg_color="transparent")
        checks.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.format_checkboxes: dict[str, ctk.CTkCheckBox] = {}
        for i, fmt in enumerate(settings.EXPORT_FORMATS):
            checks.grid_columnconfigure(i % 3, weight=1)
            checkbox = ctk.CTkCheckBox(
                checks,
                text=fmt,
                variable=self.format_vars[fmt],
            )
            checkbox.grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=6)
            self.format_checkboxes[fmt] = checkbox

        # --- Language dropdown ---
        lang_row = ctk.CTkFrame(frame, fg_color="transparent")
        lang_row.grid(row=2, column=0, sticky="w", padx=16, pady=(4, 12))

        ctk.CTkLabel(lang_row, text="Target language:").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.language_menu = ctk.CTkOptionMenu(
            lang_row,
            values=list(settings.LANGUAGES),
            variable=self.language_var,
            width=170,
        )
        self.language_menu.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(lang_row, text="Output:").grid(
            row=0, column=2, sticky="w", padx=(20, 8)
        )
        self.output_mode_menu = ctk.CTkOptionMenu(
            lang_row,
            values=list(settings.OUTPUT_MODES),
            variable=self.output_mode_var,
            width=140,
        )
        self.output_mode_menu.grid(row=0, column=3, sticky="w")

        self.study_guide_checkbox = ctk.CTkCheckBox(
            lang_row,
            text="AI study-guide prompt",
            variable=self.study_guide_var,
        )
        self.study_guide_checkbox.grid(row=0, column=4, sticky="w", padx=(20, 0))

    def _build_videos_section(self) -> None:
        """Large scrollable 'Videos Found' area."""
        self.videos_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Videos Found",
        )
        self.videos_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=8)
        self.videos_frame.grid_columnconfigure(0, weight=1)

        # Placeholder message until discovery is implemented.
        self.videos_placeholder = ctk.CTkLabel(
            self.videos_frame,
            text="No videos yet. Paste a URL and press Start.",
            text_color=("gray55", "gray60"),
        )
        self.videos_placeholder.grid(row=0, column=0, sticky="w", padx=8, pady=8)

    def _build_controls_section(self) -> None:
        """Start / Pause / Cancel buttons + progress bar."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=5, column=0, sticky="ew", padx=20, pady=8)
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        frame.grid_columnconfigure(3, weight=3)

        self.start_button = ctk.CTkButton(
            frame, text="Start", command=self._on_start
        )
        self.start_button.grid(row=0, column=0, padx=(16, 6), pady=12, sticky="ew")

        self.pause_button = ctk.CTkButton(
            frame,
            text="Pause",
            state="disabled",
            command=self._on_pause,
        )
        self.pause_button.grid(row=0, column=1, padx=6, pady=12, sticky="ew")

        self.cancel_button = ctk.CTkButton(
            frame,
            text="Cancel",
            state="disabled",
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._on_cancel,
        )
        self.cancel_button.grid(row=0, column=2, padx=6, pady=12, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.grid(row=0, column=3, padx=(6, 16), pady=12, sticky="ew")
        self.progress_bar.set(0.0)

    def _build_status_section(self) -> None:
        """Status label along the bottom."""
        self.status_label = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            anchor="w",
            text_color=("gray50", "gray65"),
        )
        self.status_label.grid(row=6, column=0, sticky="ew", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------ #
    # Videos Found helpers
    # ------------------------------------------------------------------ #
    def _clear_videos(self) -> None:
        """Remove every widget currently in the Videos Found area."""
        for widget in self.videos_frame.winfo_children():
            widget.destroy()

    def _reset_targets(self) -> None:
        """Forget any discovered videos / selection / row-status widgets."""
        self._targets = []
        self._playlist_title = None
        self.selection_vars = {}
        self.row_status = {}

    def _show_validated_video(self, result: VideoValidation) -> None:
        """Render a single validated video and register it as a download target."""
        self._clear_videos()
        self._reset_targets()

        entry = PlaylistEntry(
            position=1,
            video_id=result.video_id or "",
            title=result.title or "(untitled)",
            url=result.url,
        )
        self._targets = [entry]
        self.selection_vars[entry.video_id] = ctk.BooleanVar(value=True)

        card = ctk.CTkFrame(self.videos_frame)
        card.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=entry.title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        subtitle = f"{result.author or 'Unknown channel'}  ·  {entry.video_id}"
        ctk.CTkLabel(
            card,
            text=subtitle,
            text_color=("gray45", "gray65"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))

        status = ctk.CTkLabel(card, text="ready", text_color=("gray50", "gray65"), anchor="w")
        status.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))
        self.row_status[entry.video_id] = status

    def _show_playlist(self, playlist: Playlist) -> None:
        """Render a playlist as a selectable checklist in Videos Found."""
        self._clear_videos()
        self._reset_targets()
        self._targets = list(playlist.entries)
        self._playlist_title = playlist.title

        # Header: playlist title + count, with Select all / None controls.
        header = ctk.CTkFrame(self.videos_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=f"{playlist.title}   ({len(playlist.entries)} videos)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header, text="Select all", width=90,
            command=lambda: self._set_all_entries(True),
        ).grid(row=0, column=1, padx=4)
        ctk.CTkButton(
            header, text="None", width=70,
            command=lambda: self._set_all_entries(False),
        ).grid(row=0, column=2, padx=(4, 0))

        # One row per video: checkbox + "NN. Title" + duration + status.
        for i, entry in enumerate(playlist.entries, start=1):
            var = ctk.BooleanVar(value=True)
            self.selection_vars[entry.video_id] = var

            row = ctk.CTkFrame(self.videos_frame)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkCheckBox(row, text="", width=24, variable=var).grid(
                row=0, column=0, padx=(8, 4), pady=6
            )
            ctk.CTkLabel(
                row,
                text=f"{entry.position:02d}.  {entry.title}",
                anchor="w",
                justify="left",
            ).grid(row=0, column=1, sticky="w", padx=4)
            ctk.CTkLabel(
                row,
                text=format_duration(entry.duration),
                text_color=("gray45", "gray65"),
                width=70,
                anchor="e",
            ).grid(row=0, column=2, padx=(4, 6))

            status = ctk.CTkLabel(
                row, text="", text_color=("gray50", "gray65"), width=110, anchor="e"
            )
            status.grid(row=0, column=3, padx=(0, 10))
            self.row_status[entry.video_id] = status

    def _set_all_entries(self, value: bool) -> None:
        """Check or uncheck every video in the playlist list."""
        for var in self.selection_vars.values():
            var.set(value)

    def _selected_targets(self) -> list[PlaylistEntry]:
        """Return the PlaylistEntry objects the user has left checked."""
        return [
            entry
            for entry in self._targets
            if self.selection_vars.get(entry.video_id, None) is None
            or self.selection_vars[entry.video_id].get()
        ]

    def _update_row_status(self, video_id: str, text: str, level: str = "info") -> None:
        """Set the per-video status label (safe if the row no longer exists)."""
        label = self.row_status.get(video_id)
        if label is not None:
            label.configure(text=text, text_color=_STATUS_COLORS.get(level, _STATUS_COLORS["info"]))

    # ------------------------------------------------------------------ #
    # Mode transitions (idle: discover -> discovered: download)
    # ------------------------------------------------------------------ #
    def _enter_discovered_mode(self) -> None:
        """Switch Start into 'Download Captions' and enable Cancel."""
        self._mode = "discovered"
        self._discovered_url = self.url_var.get().strip()
        self.start_button.configure(text="Download Captions")
        self.cancel_button.configure(state="normal")

    def _enter_idle_mode(self) -> None:
        """Return Start to discovery and clear discovered state."""
        self._mode = "idle"
        self._discovered_url = ""
        self._reset_targets()
        self.start_button.configure(text="Start")
        self.cancel_button.configure(state="disabled")

    def _on_url_changed(self, *_args) -> None:
        """If the URL diverges from what was discovered, revert to discover-mode."""
        if self._mode == "discovered" and self.url_var.get().strip() != self._discovered_url:
            self._enter_idle_mode()

    def _set_busy(self, busy: bool) -> None:
        """Toggle the working state: disable Start + animate the progress bar."""
        if busy:
            self.start_button.configure(state="disabled")
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0.0)
            self.start_button.configure(state="normal")

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _set_status(self, message: str, level: str = "info") -> None:
        """Update the status label (color-coded by level) and log the message."""
        self.status_var.set(message)
        self.status_label.configure(
            text_color=_STATUS_COLORS.get(level, _STATUS_COLORS["info"])
        )
        if level == "error":
            logger.warning("Status: %s", message)
        else:
            logger.info("Status: %s", message)

    def _on_select_output_folder(self) -> None:
        """Open a directory picker and store the chosen path."""
        try:
            selected = filedialog.askdirectory(title="Select output folder")
        except Exception:  # noqa: BLE001 - Tk can raise on odd platforms
            logger.exception("Failed to open folder dialog.")
            self._set_status("Could not open the folder dialog.")
            return

        if selected:
            self.output_dir_var.set(selected)
            self._set_status(f"Output folder set: {selected}")
        else:
            logger.debug("Folder selection cancelled by user.")

    def _selected_formats(self) -> list[str]:
        """Return the list of currently-checked export formats."""
        return [fmt for fmt, var in self.format_vars.items() if var.get()]

    def _on_start(self) -> None:
        """Start button. Discovers first; once discovered, downloads captions."""
        if self._mode == "discovered":
            self._begin_download()
        else:
            self._begin_discovery()

    def _begin_discovery(self) -> None:
        """Validate a single URL or enumerate a playlist (background thread)."""
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Please enter a YouTube URL first.", level="error")
            return

        parsed = parse_youtube_url(url)
        self._set_busy(True)

        if parsed.kind == "playlist":
            logger.info("Reading playlist: %r", url)
            self._set_status("Reading playlist…", level="info")
            worker = self._run_playlist
        else:
            # Video and invalid URLs both go through single-video validation,
            # which produces the right friendly message for each.
            logger.info("Validating URL: %r", url)
            self._set_status("Validating URL…", level="info")
            worker = self._run_validation

        threading.Thread(target=worker, args=(url,), daemon=True).start()

    def _run_validation(self, url: str) -> None:
        """Worker-thread body. Must NOT touch Tk widgets directly."""
        try:
            result = validate_single_video(url)
        except Exception as exc:  # noqa: BLE001 - never let the worker die silently
            logger.exception("URL validation crashed.")
            result = VideoValidation(
                ok=False,
                url=url,
                status="error",
                message=f"Unexpected error during validation: {exc}",
            )
        # Marshal back onto the GUI thread.
        self.after(0, self._on_validation_done, result)

    def _on_validation_done(self, result: VideoValidation) -> None:
        """Runs on the Tk main thread once validation finishes."""
        self._set_busy(False)
        if result.ok:
            self._show_validated_video(result)
            self._enter_discovered_mode()
            self._set_status(f"✓ {result.message}", level="success")
        else:
            self._enter_idle_mode()
            self._set_status(f"✗ {result.message}", level="error")

    def _run_playlist(self, url: str) -> None:
        """Worker-thread body for playlist enumeration. No Tk calls here."""
        try:
            result = fetch_playlist(url)
        except Exception as exc:  # noqa: BLE001 - keep the worker crash-proof
            logger.exception("Playlist enumeration crashed.")
            result = Playlist(
                ok=False, playlist_id=None, title="", status="error",
                message=f"Unexpected error reading playlist: {exc}",
            )
        self.after(0, self._on_playlist_done, result)

    def _on_playlist_done(self, result: Playlist) -> None:
        """Runs on the Tk main thread once playlist enumeration finishes."""
        self._set_busy(False)
        if result.ok:
            self._show_playlist(result)
            self._enter_discovered_mode()
            self._set_status(f"✓ {result.message}", level="success")
        else:
            self._enter_idle_mode()
            self._set_status(f"✗ {result.message}", level="error")

    # ------------------------------------------------------------------ #
    # Caption download (Phases 4-5)
    # ------------------------------------------------------------------ #
    def _begin_download(self) -> None:
        """Download captions for the selected videos, with retry + progress."""
        targets = self._selected_targets()
        if not targets:
            self._set_status("Select at least one video to download.", level="error")
            return

        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            self._set_status("Select an output folder before downloading.", level="error")
            return

        target_code = settings.LANGUAGE_CODES.get(self.language_var.get(), "en")
        target_display = self.language_var.get()
        output_mode = self.output_mode_var.get()

        # Phase 6: where Markdown + raw captions land, and how files are named.
        if self._playlist_title:
            dest_dir = str(Path(output_dir) / sanitize_filename(self._playlist_title))
            numbered = True
        else:
            dest_dir = output_dir
            numbered = False
        markdown_enabled = self.format_vars["Markdown"].get()
        speechify_enabled = self.format_vars["Speechify Formatting"].get()
        export_formats = {
            label for label in EXPORT_LABELS if self.format_vars[label].get()
        }
        study_guide_enabled = self.study_guide_var.get()
        date_str = date.today().isoformat()

        logger.info(
            "Downloading %d video(s): target=%s mode=%s dest=%r md=%s sp=%s exports=%s guide=%s",
            len(targets), target_code, output_mode, dest_dir,
            markdown_enabled, speechify_enabled, sorted(export_formats), study_guide_enabled,
        )

        self._cancel_event.clear()
        self._pause_event.clear()
        self._downloading = True
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause")
        self.cancel_button.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0.0)
        for entry in targets:
            self._update_row_status(entry.video_id, "queued", "info")
        self._set_status(f"Starting… 0/{len(targets)}", level="info")

        threading.Thread(
            target=self._run_download,
            args=(targets, target_code, target_display, output_mode, dest_dir,
                  markdown_enabled, speechify_enabled, export_formats, study_guide_enabled,
                  numbered, date_str),
            daemon=True,
        ).start()

    def _run_download(
        self, targets, target_code: str, target_display: str, output_mode: str, dest_dir: str,
        markdown_enabled: bool, speechify_enabled: bool, export_formats: set,
        study_guide_enabled: bool, numbered: bool, date_str: str,
    ) -> None:
        """Worker thread: download each video with retry, then write Markdown."""
        total = len(targets)
        completed = failed = processed = 0
        index_items: list[tuple[int, str, str]] = []

        for entry in targets:
            if self._cancel_event.is_set():
                break
            self._wait_if_paused()
            if self._cancel_event.is_set():
                break

            vid = entry.video_id
            self.after(0, self._update_row_status, vid, "downloading…", "info")

            def _on_retry(attempt, _max, delay, _status, _vid=vid):
                self.after(
                    0, self._update_row_status, _vid,
                    f"retry {attempt} in {int(delay)}s", "info",
                )

            try:
                result, body_override, lang_display = self._resolve_captions(
                    entry, target_code, target_display, output_mode, dest_dir, _on_retry,
                )
            except Exception as exc:  # noqa: BLE001 - one bad video must not stop the batch
                logger.exception("Caption download crashed for %s", vid)
                result = CaptionResult(vid, "error", message=str(exc))
                body_override, lang_display = None, target_display

            if result.status == "cancelled":
                break

            processed += 1
            tags: list[str] = []
            if result.status == "ok":
                completed += 1
                if markdown_enabled:
                    try:
                        md_path = write_video_markdown(
                            entry, result, dest_dir,
                            date_str=date_str, language_display=lang_display,
                            numbered=numbered, body_override=body_override,
                        )
                        tags.append("md")
                        index_items.append((entry.position, entry.title, md_path.name))
                    except Exception:  # noqa: BLE001 - md failure must not stop the batch
                        logger.exception("Markdown generation failed for %s", vid)
                        tags.append("md failed")
                if speechify_enabled:
                    try:
                        write_video_markdown(
                            entry, result, dest_dir,
                            date_str=date_str, language_display=lang_display,
                            numbered=numbered, speechify=True,
                        )
                        tags.append("sp")
                    except Exception:  # noqa: BLE001 - speechify failure is non-fatal
                        logger.exception("Speechify generation failed for %s", vid)
                        tags.append("sp failed")
                if export_formats:
                    export_results = export_video(
                        entry, result, dest_dir,
                        formats=export_formats,
                        date_str=date_str, language_display=lang_display,
                        numbered=numbered, body_override=body_override,
                    )
                    for label in sorted(export_results):
                        ok = export_results[label]
                        tags.append(label.lower() if ok else f"{label.lower()} failed")
                if study_guide_enabled:
                    try:
                        write_study_guide_prompt(
                            entry, result, dest_dir,
                            date_str=date_str, language_display=lang_display,
                            numbered=numbered, body_override=body_override,
                        )
                        tags.append("guide")
                    except Exception:  # noqa: BLE001 - guide failure is non-fatal
                        logger.exception("Study-guide prompt failed for %s", vid)
                        tags.append("guide failed")
            else:
                failed += 1
            self.after(
                0, self._apply_caption_result,
                result, processed, total, completed, failed, " · ".join(tags),
            )

            # Polite pause between videos (interruptible), except after the last.
            if processed < total and not self._cancel_event.is_set():
                self._cancel_event.wait(settings.DOWNLOAD_DELAY)

        if markdown_enabled and numbered and index_items:
            try:
                write_playlist_index(self._playlist_title or "Playlist", index_items, dest_dir)
            except Exception:  # noqa: BLE001 - index is optional
                logger.exception("Failed to write playlist index.")

        self.after(0, self._on_download_done, completed, failed, total, self._cancel_event.is_set())

    @staticmethod
    def _lang_base(code: str | None) -> str:
        """Base language subtag, lowercased (e.g. 'en-US' -> 'en')."""
        return (code or "").split("-")[0].split(".")[0].lower()

    def _lang_display(self, code: str | None) -> str:
        """Human-readable language name for an ISO code (falls back to the code)."""
        if not code:
            return "Unknown"
        return self._code_to_lang.get(self._lang_base(code), code)

    def _resolve_captions(
        self, entry, target_code: str, target_display: str,
        mode: str, dest_dir: str, on_retry,
    ):
        """Download caption(s) per output mode. Returns (result, body_override, label).

        Runs on the worker thread. Uses YouTube's own translations: selecting a
        target language yields its (possibly auto-translated) track.
        """
        def _dl(lang_code):
            return download_captions(
                entry.video_id, lang_code, dest_dir,
                cancel_event=self._cancel_event, on_retry=on_retry,
            )

        if mode == "Original":
            result = _dl(ORIGINAL_LANG)
            return result, None, self._lang_display(result.original_language) or target_display

        if mode == "Bilingual":
            translated = _dl(target_code)
            if translated.status != "ok":
                return translated, None, target_display
            original_code = translated.original_language
            if original_code and self._lang_base(original_code) != self._lang_base(target_code):
                original = _dl(ORIGINAL_LANG)
                if original.status == "ok":
                    body = build_bilingual_body(
                        original.path, self._lang_display(original_code),
                        translated.path, target_display,
                    )
                    label = f"{self._lang_display(original_code)} + {target_display} (bilingual)"
                    return translated, body, label
                return translated, None, f"{target_display} (translated; original unavailable)"
            # Original and target are the same language — nothing to pair.
            return translated, None, target_display

        # "Translated" (default): download the target-language track.
        result = _dl(target_code)
        if result.status == "ok":
            original_code = result.original_language
            if original_code and self._lang_base(original_code) != self._lang_base(target_code):
                return result, None, f"{target_display} (translated from {self._lang_display(original_code)})"
        return result, None, target_display

    def _wait_if_paused(self) -> None:
        """Block the worker thread while paused; break out if cancelled."""
        announced = False
        while self._pause_event.is_set() and not self._cancel_event.is_set():
            if not announced:
                self.after(0, self._set_status, "Paused.", "info")
                announced = True
            self._cancel_event.wait(0.2)

    @staticmethod
    def _caption_display(result: CaptionResult) -> tuple[str, str]:
        """Map a CaptionResult to (row text, status level)."""
        mapping = {
            "no_captions": ("no captions", "info"),
            "unavailable": ("unavailable", "error"),
            "rate_limited": ("rate limited", "error"),
            "network_error": ("network error", "error"),
            "cancelled": ("cancelled", "info"),
        }
        if result.status == "ok":
            return f"✓ {result.kind}", "success"
        return mapping.get(result.status, ("error", "error"))

    def _apply_caption_result(
        self, result: CaptionResult, processed: int, total: int,
        completed: int, failed: int, extra: str = "",
    ) -> None:
        """Runs on the Tk main thread after each video finishes."""
        text, level = self._caption_display(result)
        if extra:
            text = f"{text} · {extra}"
        self._update_row_status(result.video_id, text, level)
        self.progress_bar.set(processed / total if total else 0.0)
        remaining = total - processed
        self._set_status(
            f"Downloading… {processed}/{total}  "
            f"(ok {completed}, failed {failed}, remaining {remaining})",
            level="info",
        )

    def _on_download_done(self, completed: int, failed: int, total: int, cancelled: bool) -> None:
        """Runs on the Tk main thread once the batch finishes (or is cancelled)."""
        self._downloading = False
        self.pause_button.configure(state="disabled", text="Pause")
        self.start_button.configure(state="normal")   # stays in discovered mode
        self.cancel_button.configure(state="normal")
        self.progress_bar.set(0.0 if cancelled else 1.0)

        if cancelled:
            remaining = total - completed - failed
            self._set_status(
                f"Cancelled. {completed} ok, {failed} failed, {remaining} skipped.",
                level="info",
            )
        elif failed == 0:
            self._set_status(f"✓ Downloaded captions for all {total} video(s).", level="success")
        elif completed == 0:
            self._set_status(f"✗ No captions downloaded ({failed} failed/unavailable).", level="error")
        else:
            self._set_status(
                f"Done: {completed} ok, {failed} failed or had no captions.", level="info"
            )

    def _on_pause(self) -> None:
        """Toggle pause/resume during an active download."""
        if not self._downloading:
            self._set_status("Nothing to pause.", level="info")
            return
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.pause_button.configure(text="Pause")
            self._set_status("Resuming…", level="info")
        else:
            self._pause_event.set()
            self.pause_button.configure(text="Resume")
            logger.info("Download paused.")

    def _on_cancel(self) -> None:
        """Cancel an active download, or clear results when idle."""
        if self._downloading:
            logger.info("Cancel requested (download in progress).")
            self._cancel_event.set()
            self._pause_event.clear()  # let a paused loop observe the cancel
            self._set_status("Cancelling…", level="info")
            return

        logger.info("Cancel requested (reset view).")
        self._enter_idle_mode()
        self._clear_videos()
        self.videos_placeholder = ctk.CTkLabel(
            self.videos_frame,
            text="No videos yet. Paste a URL and press Start.",
            text_color=("gray55", "gray60"),
        )
        self.videos_placeholder.grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0.0)
        self._set_status("Ready.", level="info")
