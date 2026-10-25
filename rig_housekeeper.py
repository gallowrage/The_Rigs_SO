from __future__ import annotations

import concurrent.futures
import os
import queue
import shutil
from pathlib import Path
import customtkinter as ctk

# --- SYNCHRONIZED RULES ENGINE ---

# The Quarantine Array: Protects OS, DAW UIs, and Game Assets
EXCLUSIONS = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "system volume information",
    "$recycle.bin",
    "recovery",
    "perflogs",
    "steamlibrary",
    "steam library",
    "steamapps",
    "vstplugins",
    "steinberg",
    "user library",
    "world of warcraft",
    "guild wars",
    "fortnite",
    "amongus",
    "dragonball",
    "master_archive",
    "master_video_archive",
    "master_music_archive",
}

# The Unified Category Extensions
CATEGORIES = {
    "Documents": (".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx", ".rtf", ".odt", ".ppt", ".pptx"),
    "Images": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".raw", ".dng"),
    "Audio": (".wav", ".mp3", ".midi", ".mid", ".flp", ".als", ".aiff", ".aif", ".flac", ".m4a", ".ogg", ".wma", ".aac", ".opus"),
    "Video": (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg", ".webm", ".3gp"),
}

ARCHIVE_PATHS = {
    "Documents": r"E:\Master_Archive\Documents",
    "Images": r"E:\Master_Archive\Images",
    "Audio": r"E:\Master_Music_Archive",
    "Video": r"E:\Master_Video_Archive",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class RigHousekeeperApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Rig Housekeeper - Native Concurrency Engine")
        self.geometry("960x680")
        self.minsize(800, 550)

        # Concurrency & Queue State
        self.log_queue: queue.Queue[str | tuple[str, ...]] = queue.Queue()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="RigHousekeeper")
        self._cancel_flag = False
        self._is_running = False

        self._build_ui()
        self.after(100, self.poll_queue)

    def _build_ui(self) -> None:
        # Title Header
        header = ctk.CTkFrame(self, corner_radius=8, fg_color="#18222d")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title = ctk.CTkLabel(
            header,
            text="The Rig's Housekeeper",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#edf3fa",
        )
        title.pack(anchor="w", padx=16, pady=(12, 2))

        subtitle = ctk.CTkLabel(
            header,
            text="Native in-process file engine. Zero PowerShell / WinForms dependency. Zero disk JSON overhead.",
            font=ctk.CTkFont(size=12),
            text_color="#9bb0c4",
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 12))

        # Main Control Layout
        controls_frame = ctk.CTkFrame(self, corner_radius=8)
        controls_frame.pack(fill="x", padx=16, pady=6)

        # Drive Selection
        drive_label = ctk.CTkLabel(
            controls_frame,
            text="Target Source Drives / Roots:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        drive_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))

        drives_subframe = ctk.CTkFrame(controls_frame, fg_color="transparent")
        drives_subframe.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        self.drive_vars: dict[str, ctk.BooleanVar] = {}
        for drive in ("C:\\", "D:\\", "E:\\"):
            var = ctk.BooleanVar(value=True if drive in ("C:\\", "D:\\") else False)
            self.drive_vars[drive] = var
            chk = ctk.CTkCheckBox(drives_subframe, text=f"Drive {drive}", variable=var)
            chk.pack(side="left", padx=(0, 14))

        # Action Buttons & Status
        action_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        action_frame.grid(row=1, column=1, sticky="e", padx=16, pady=(0, 12))

        self.start_button = ctk.CTkButton(
            action_frame,
            text="Run File Engine",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2970c2",
            hover_color="#3a86dd",
            command=self.on_start_clicked,
        )
        self.start_button.pack(side="left", padx=6)

        self.cancel_button = ctk.CTkButton(
            action_frame,
            text="Cancel",
            fg_color="#8d3c3c",
            hover_color="#aa4b4b",
            state="disabled",
            command=self.on_cancel_clicked,
        )
        self.cancel_button.pack(side="left", padx=6)

        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=0)

        # Target Archive Directory Info
        archive_info = ctk.CTkFrame(self, corner_radius=8, fg_color="#141c24")
        archive_info.pack(fill="x", padx=16, pady=6)

        info_text = (
            f"Archiving to: Documents -> {ARCHIVE_PATHS['Documents']}  |  "
            f"Images -> {ARCHIVE_PATHS['Images']}  |  "
            f"Audio -> {ARCHIVE_PATHS['Audio']}  |  "
            f"Video -> {ARCHIVE_PATHS['Video']}"
        )
        ctk.CTkLabel(
            archive_info,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="#8397aa",
        ).pack(anchor="w", padx=14, pady=8)

        # Progress Indicator
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=16, pady=(8, 4))
        self.progress_bar.set(0)

        # Terminal Output Box
        self.log_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0e1318",
            text_color="#c8d6e5",
            corner_radius=8,
        )
        self.log_box.pack(expand=True, fill="both", padx=16, pady=(4, 16))
        self.log_box.insert("end", "[INITIALIZED] Rig Housekeeper Native Concurrency Engine ready.\n")
        self.log_box.configure(state="disabled")

    def poll_queue(self) -> None:
        """Safely extracts log messages from the background thread to update the UI."""
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_box.configure(state="normal")
            if isinstance(msg, str):
                self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(100, self.poll_queue)

    def on_start_clicked(self) -> None:
        selected_drives = [drive for drive, var in self.drive_vars.items() if var.get()]
        if not selected_drives:
            self.log_queue.put("[ERROR] No source drives selected.")
            return

        self._cancel_flag = False
        self._is_running = True
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress_bar.start()

        self.trigger_scan(selected_drives)

    def on_cancel_clicked(self) -> None:
        if self._is_running:
            self._cancel_flag = True
            self.log_queue.put("[SYSTEM] Cancellation requested. Halting traversal...")
            self.cancel_button.configure(state="disabled")

    def trigger_scan(self, source_drives: list[str]) -> None:
        """Dispatches the background thread worker."""
        self.log_queue.put("[SYSTEM] Initializing unified native file engine...")

        # Ensure master directories exist
        for path in ARCHIVE_PATHS.values():
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as err:
                self.log_queue.put(f"[WARNING] Could not verify path {path}: {err}")

        self.executor.submit(self._background_file_worker, source_drives)

    def _resolve_unique_dest_path(self, dest_folder: str, file: str) -> tuple[str, int]:
        """Resolves collision by adding incrementing counter suffix."""
        base, ext_orig = os.path.splitext(file)
        dest_path = os.path.join(dest_folder, file)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext_orig}")
            counter += 1
        return dest_path, counter

    def _move_file_to_archive(
        self, source_path: str, dest_path: str, file: str, target_category: str, counter: int
    ) -> tuple[int, int]:
        """Moves file to target archive destination and reports collisions."""
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(source_path, dest_path)
            if counter > 1:
                self.log_queue.put(
                    f"[COLLISION RESOLVED] {file} -> {os.path.basename(dest_path)}"
                )
                return 1, 1
            self.log_queue.put(f"[MOVED] {file} -> {target_category}")
            return 1, 0
        except Exception as e:
            self.log_queue.put(f"[ERROR] Failed to move {file}: {e}")
            return 0, 0

    def _process_candidate_file(self, root: str, file: str) -> tuple[int, int, int]:
        """Categorizes and dispatches a single file for archiving."""
        ext = os.path.splitext(file)[1].lower()
        target_category = next(
            (cat for cat, exts in CATEGORIES.items() if ext in exts), None
        )
        if not target_category:
            return 0, 0, 1

        source_path = os.path.join(root, file)
        dest_folder = ARCHIVE_PATHS[target_category]
        dest_path, counter = self._resolve_unique_dest_path(dest_folder, file)
        moved, coll = self._move_file_to_archive(
            source_path, dest_path, file, target_category, counter
        )
        return moved, coll, 0

    def _process_dir_files(self, root: str, files: list[str]) -> tuple[int, int, int]:
        """Processes files in a single directory."""
        moved_t, coll_t, skip_t = 0, 0, 0
        for file in files:
            if self._cancel_flag:
                break
            m, c, s = self._process_candidate_file(root, file)
            moved_t += m
            coll_t += c
            skip_t += s
        return moved_t, coll_t, skip_t

    def _filter_excluded_dirs(self, root: str, dirs: list[str]) -> bool:
        """Evaluates directory exclusions. Returns True if root itself should be skipped."""
        root_lower = root.lower()
        if any(exclusion in root_lower for exclusion in EXCLUSIONS):
            dirs[:] = []
            return True
        dirs[:] = [
            d for d in dirs
            if not any(exclusion in d.lower() for exclusion in EXCLUSIONS)
        ]
        return False

    def _scan_single_drive(self, drive: str) -> tuple[int, int, int]:
        """Walks and archives matching files across one drive."""
        moved_t, coll_t, skip_t = 0, 0, 0
        if not os.path.exists(drive):
            self.log_queue.put(f"[WARNING] Source drive unavailable: {drive}")
            return 0, 0, 0

        self.log_queue.put(f"\n--- Scanning Surface of {drive} ---")
        for root, dirs, files in os.walk(drive):
            if self._cancel_flag:
                self.log_queue.put("[SYSTEM] Traversal halted by user.")
                break
            if self._filter_excluded_dirs(root, dirs):
                continue
            m, c, s = self._process_dir_files(root, files)
            moved_t += m
            coll_t += c
            skip_t += s
        return moved_t, coll_t, skip_t

    def _background_file_worker(self, source_drives: list[str]) -> None:
        """The native Python file engine. Runs entirely in-process off the main UI thread."""
        moved_count = 0
        collision_count = 0
        skipped_count = 0

        try:
            for drive in source_drives:
                if self._cancel_flag:
                    break
                m, c, s = self._scan_single_drive(drive)
                moved_count += m
                collision_count += c
                skipped_count += s

            summary = (
                f"\n[SUCCESS] File engine traversal complete.\n"
                f"Total Moved: {moved_count} | Collisions Handled: {collision_count} | Untargeted Files Skipped: {skipped_count}"
            )
            self.log_queue.put(summary)
        except Exception as exc:
            self.log_queue.put(f"\n[FATAL ERROR] Engine exception: {exc}")
        finally:
            self._is_running = False
            self.after(0, self._on_worker_finished)

    def _on_worker_finished(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")


def main() -> None:
    app = RigHousekeeperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
