from __future__ import annotations

import argparse
import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter
customtkinter.set_appearance_mode("dark")
theme_path = os.path.join(os.path.dirname(__file__), "vane_theme.json")
if os.path.exists(theme_path):
    customtkinter.set_default_color_theme(theme_path)

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_starter.drive_organizer import scan_archive_inventory

try:
    from personal_agent.config import DOCS_DIR
    DEFAULT_ROOTS = [str(DOCS_DIR)]
except ImportError:
    DEFAULT_ROOTS = [
        "C:/Users",
        "D:/Games",
        "D:/SteamLibrary",
        "E:/Music",
        "E:/Photos",
        "E:/Documents",
        "E:/Master_Archive",
    ]
DEFAULT_ARCHIVE_DESTINATION = "E:/Master_Archive"
ARCHIVE_CATEGORIES = ("Documents", "Images", "Audio", "Video", "Archives", "Software")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review drive and folder inventories, flag large files, and organize selected files by type."
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=DEFAULT_ROOTS,
        help="Folders to scan. Defaults to the housekeeping roots used by the organizer.",
    )
    parser.add_argument(
        "--mode",
        choices=["housekeeping", "organize", "archive"],
        default="housekeeping",
        help="Run organizer mode. Housekeeping is the default and focuses on user-owned data roots.",
    )
    parser.add_argument(
        "--destination",
        default=DEFAULT_ARCHIVE_DESTINATION,
        help="Base archive folder used by archive mode.",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=ARCHIVE_CATEGORIES,
        default=list(ARCHIVE_CATEGORIES),
        help="File categories to include in archive mode.",
    )
    parser.add_argument(
        "--large-file-mb",
        type=float,
        default=1024,
        help="Flag files at or above this size for review.",
    )
    parser.add_argument(
        "--include-protected",
        action="store_true",
        help="Also scan named system, install, and game folders normally skipped.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files instead of printing a dry-run plan.",
    )
    parser.add_argument(
        "--log-file",
        default="housekeeping_log.txt",
        help="File path used to capture the organizer output.",
    )
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    project_root = Path(__file__).resolve().parent
    script_path = project_root / "src" / "python_starter" / "drive_organizer.py"
    command = [
        sys.executable,
        str(script_path),
        "--mode",
        args.mode,
    ]
    if args.roots:
        command.extend(["--roots", *args.roots])
    if args.mode == "archive":
        command.extend(["--destination", str(args.destination)])
        command.extend(["--categories", *args.categories])
        command.extend(["--large-file-mb", str(args.large_file_mb)])
        if getattr(args, "include_protected", False):
            command.append("--include-protected")
        if getattr(args, "plan_output", None):
            command.extend(["--plan-output", str(args.plan_output)])
        if getattr(args, "execute_plan", None):
            command.extend(["--execute-plan", str(args.execute_plan)])
    if args.execute:
        command.append("--execute")
    return command


def write_log_file(log_path: str | Path, text: str) -> Path:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class HousekeepingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("File Organizer")
        self.root.geometry("1020x760")
        self.root.minsize(880, 620)
        self.root.configure(bg="#101418")
        self.root.overrideredirect(True)

        self.root_vars: dict[str, tk.BooleanVar] = {}
        self.root_entries: list[str] = []
        self.destination_var = tk.StringVar(value=DEFAULT_ARCHIVE_DESTINATION)
        self.category_vars = {
            category: tk.BooleanVar(value=True) for category in ARCHIVE_CATEGORIES
        }
        self.large_file_var = tk.StringVar(value="1024")
        self.include_protected_var = tk.BooleanVar(value=False)
        self.file_filter_var = tk.StringVar()
        self.plan_operations: list[dict[str, str | int | bool]] = []
        self.folder_records: list[dict[str, str | int | bool]] = []
        self.checked_plan_items: set[int] = set()
        self.folder_paths: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="HousekeeperWorker")
        self._work_queue: queue.Queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._is_running = False
        self._close_when_finished = False

        self.dark_bg = "#101418"
        self.panel_bg = "#1b2430"
        self.panel_alt = "#222d38"
        self.text_fg = "#edf3fa"
        self.muted_fg = "#b4c2d1"
        self.accent = "#4ea1ff"
        self.success = "#1f7a5d"
        self.warn = "#d98b2b"
        self.fail = "#d95b5b"

        self.title_bar = tk.Frame(root, bg="#171e27", height=42, highlightthickness=0)
        self.title_bar.pack(fill="x")
        self.title_bar_title = tk.Label(
            self.title_bar,
            text="File Organizer",
            bg="#171e27",
            fg="#f4f7fb",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            padx=14,
        )
        self.title_bar_title.pack(side="left", fill="x", expand=True)

        self.minimize_button = tk.Button(
            self.title_bar,
            text="—",
            width=3,
            bg="#171e27",
            fg="#edf3fa",
            bd=0,
            activebackground="#2a333d",
            activeforeground="#ffffff",
            command=self.root.iconify,
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
        )
        self.minimize_button.pack(side="right", padx=(0, 4), pady=6)
        self.minimize_button.bind(
            "<Enter>", lambda event: self.minimize_button.configure(bg="#2a333d")
        )
        self.minimize_button.bind(
            "<Leave>", lambda event: self.minimize_button.configure(bg="#171e27")
        )

        self.close_button = tk.Button(
            self.title_bar,
            text="✕",
            width=3,
            bg="#171e27",
            fg="#edf3fa",
            bd=0,
            activebackground="#a33a3a",
            activeforeground="#ffffff",
            command=self.close_app,
            relief="flat",
            highlightthickness=0,
            cursor="hand2",
        )
        self.close_button.pack(side="right", padx=(0, 10), pady=6)
        self.close_button.bind(
            "<Enter>", lambda event: self.close_button.configure(bg="#a33a3a")
        )
        self.close_button.bind(
            "<Leave>", lambda event: self.close_button.configure(bg="#171e27")
        )

        self.title_bar.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._drag_window)
        self.title_bar_title.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar_title.bind("<B1-Motion>", self._drag_window)

        self.window_frame = tk.Frame(root, bg=self.dark_bg)
        self.window_frame.pack(fill="both", expand=True)

        self.resize_handle = tk.Label(
            root,
            text="◢",
            bg="#171e27",
            fg="#99a8b5",
            font=("Segoe UI", 12),
            cursor="sizing",
            bd=0,
            relief="flat",
        )
        self.resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)
        self.resize_handle.bind("<ButtonPress-1>", self._start_resize)
        self.resize_handle.bind("<B1-Motion>", self._resize_window)

        header = ttk.Frame(self.window_frame, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(22, 18))
        ttk.Label(
            header,
            text="Keep your drives tidy.",
            style="Hero.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Choose folders to scan. Review a dry run before moving anything.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self.window_frame, style="App.TFrame")
        content.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        content.columnconfigure(0, weight=4, uniform="content")
        content.columnconfigure(1, weight=6, uniform="content")
        content.rowconfigure(0, weight=1)

        roots_panel = ttk.Frame(content, style="Panel.TFrame", padding=18)
        roots_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        roots_panel.columnconfigure(0, weight=1)
        roots_panel.rowconfigure(3, weight=1)

        roots_heading = ttk.Frame(roots_panel, style="Panel.TFrame")
        roots_heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(roots_heading, text="Scan locations", style="Section.TLabel").pack(
            side="left"
        )
        self.selection_summary = ttk.Label(roots_heading, text="", style="Muted.TLabel")
        self.selection_summary.pack(side="right")

        ttk.Label(
            roots_panel,
            text="Select the folders you want to organize.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        controls = ttk.Frame(roots_panel, style="Panel.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(
            controls,
            text="Add folder",
            command=self.add_custom_root,
            style="Primary.TButton",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Select all", command=self.select_all).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(controls, text="Clear", command=self.clear_all).pack(side="left")

        self.check_frame = ttk.Frame(roots_panel, style="Panel.TFrame")
        self.check_frame.grid(row=3, column=0, sticky="nsew")
        self.check_frame.rowconfigure(0, weight=1)
        self.check_frame.columnconfigure(0, weight=1)
        self.root_list_canvas = tk.Canvas(
            self.check_frame,
            bg=self.panel_bg,
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=28,
        )
        root_scrollbar = ttk.Scrollbar(
            self.check_frame,
            orient="vertical",
            command=self.root_list_canvas.yview,
        )
        self.root_list_canvas.configure(yscrollcommand=root_scrollbar.set)
        self.root_list_canvas.grid(row=0, column=0, sticky="nsew")
        root_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.root_list_frame = ttk.Frame(self.root_list_canvas, style="Panel.TFrame")
        self._root_list_window = self.root_list_canvas.create_window(
            (0, 0),
            window=self.root_list_frame,
            anchor="nw",
        )
        self.root_list_frame.bind("<Configure>", self._update_root_scrollregion)
        self.root_list_canvas.bind("<Configure>", self._resize_root_list)
        self.root_list_canvas.bind("<Enter>", self._bind_root_scroll)
        self.root_list_canvas.bind("<Leave>", self._unbind_root_scroll)

        ttk.Label(
            roots_panel,
            text="Archive destination",
            style="Section.TLabel",
        ).grid(row=4, column=0, sticky="w", pady=(14, 5))
        destination_controls = ttk.Frame(roots_panel, style="Panel.TFrame")
        destination_controls.grid(row=5, column=0, sticky="ew")
        destination_controls.columnconfigure(0, weight=1)
        self.destination_entry = ttk.Entry(
            destination_controls, textvariable=self.destination_var
        )
        self.destination_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            destination_controls,
            text="Browse",
            command=self.choose_destination,
        ).grid(row=0, column=1)

        right_column = ttk.Frame(content, style="App.TFrame")
        right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(3, weight=1)

        progress_frame = ttk.Frame(right_column, style="Panel.TFrame", padding=16)
        progress_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        progress_frame.columnconfigure(0, weight=1)
        self.status_banner = tk.Label(
            progress_frame,
            text="STATUS: READY",
            bg=self.success,
            fg="#e8fff1",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=10,
            anchor="w",
            relief="flat",
            bd=0,
        )
        self.status_banner.grid(row=0, column=0, sticky="ew")
        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready when you are.",
            style="Muted.TLabel",
        )
        self.progress_label.grid(row=1, column=0, sticky="w", pady=(10, 4))
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100,
            value=0,
        )
        self.progress_bar.grid(row=2, column=0, sticky="ew")

        action_panel = ttk.Frame(right_column, style="Panel.TFrame", padding=16)
        action_panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(action_panel, text="Organize by file type", style="Section.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            action_panel,
            text="Browse scan results and select individual files to move, including large or uncommon ones. Protected system, install, and game folders stay out unless you include them below.",
            style="Muted.TLabel",
            wraplength=470,
        ).pack(anchor="w", pady=(4, 12))

        category_controls = ttk.Frame(action_panel, style="Panel.TFrame")
        category_controls.pack(fill="x", pady=(0, 10))
        for index, category in enumerate(ARCHIVE_CATEGORIES):
            ttk.Checkbutton(
                category_controls,
                text=category,
                variable=self.category_vars[category],
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 18))

        large_file_controls = ttk.Frame(action_panel, style="Panel.TFrame")
        large_file_controls.pack(fill="x", pady=(2, 10))
        ttk.Label(
            large_file_controls,
            text="Flag large files at (MB):",
            style="Muted.TLabel",
        ).pack(side="left")
        ttk.Entry(
            large_file_controls,
            textvariable=self.large_file_var,
            width=9,
        ).pack(side="left", padx=(8, 0))

        ttk.Checkbutton(
            action_panel,
            text="Include protected folders (system, install, game)",
            variable=self.include_protected_var,
            command=self._confirm_include_protected,
        ).pack(anchor="w", pady=(0, 10))

        action_bar = ttk.Frame(action_panel, style="Panel.TFrame")
        action_bar.pack(fill="x")
        self.dry_run_button = ttk.Button(
            action_bar,
            text="Preview changes",
            command=lambda: self.run_organizer(execute=False),
            style="Primary.TButton",
        )
        self.dry_run_button.pack(side="left")
        self.execute_button = ttk.Button(
            action_bar,
            text="Move selected",
            command=lambda: self.run_organizer(execute=True),
            style="Danger.TButton",
        )
        self.execute_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            action_bar, text="Cancel run", command=self.stop_run
        )
        self.stop_button.pack(side="right")
        self.restart_button = ttk.Button(
            action_bar, text="Reset", command=self.restart_app
        )
        self.restart_button.pack(side="right", padx=(0, 8))
        self._set_run_controls(running=False)

        log_panel = ttk.Frame(right_column, style="Panel.TFrame", padding=16)
        log_panel.grid(row=3, column=0, sticky="nsew")
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(0, weight=1)
        self.inventory_notebook = ttk.Notebook(log_panel)
        self.inventory_notebook.grid(row=0, column=0, sticky="nsew")

        files_tab = ttk.Frame(self.inventory_notebook, padding=8)
        files_tab.columnconfigure(0, weight=1)
        files_tab.rowconfigure(1, weight=1)
        self.inventory_notebook.add(files_tab, text="Files")
        file_toolbar = ttk.Frame(files_tab)
        file_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(file_toolbar, text="Filter:").pack(side="left")
        file_filter = ttk.Entry(file_toolbar, textvariable=self.file_filter_var, width=24)
        file_filter.pack(side="left", padx=(5, 12))
        ttk.Button(
            file_toolbar,
            text="Select movable",
            command=self.select_movable_files,
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            file_toolbar,
            text="Clear selection",
            command=self.clear_file_selection,
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            file_toolbar,
            text="Open location",
            command=self.open_selected_file_location,
        ).pack(side="left")
        self.file_tree = ttk.Treeview(
            files_tab,
            columns=("include", "category", "name", "size", "large", "source", "destination"),
            show="headings",
            selectmode="browse",
        )
        for column, heading, width in (
            ("include", "Move", 48),
            ("category", "Type", 100),
            ("name", "File name", 165),
            ("size", "Size", 85),
            ("large", "Flag", 68),
            ("source", "Current folder / path", 300),
            ("destination", "Planned destination", 300),
        ):
            self.file_tree.heading(column, text=heading)
            self.file_tree.column(column, width=width, minwidth=48, stretch=column in {"name", "source", "destination"})
        self.file_tree.grid(row=1, column=0, sticky="nsew")
        file_scroll_y = ttk.Scrollbar(files_tab, orient="vertical", command=self.file_tree.yview)
        file_scroll_y.grid(row=1, column=1, sticky="ns")
        file_scroll_x = ttk.Scrollbar(files_tab, orient="horizontal", command=self.file_tree.xview)
        file_scroll_x.grid(row=2, column=0, sticky="ew")
        self.file_tree.configure(yscrollcommand=file_scroll_y.set, xscrollcommand=file_scroll_x.set)
        self.file_tree.bind("<Button-1>", self.toggle_file_selection)
        self.file_tree.bind("<Double-1>", self.open_selected_file_location)
        self.file_filter_var.trace_add("write", self.refresh_file_rows)
        self.file_summary = ttk.Label(files_tab, text="Scan to build a file inventory.")
        self.file_summary.grid(row=3, column=0, sticky="w", pady=(5, 0))

        folders_tab = ttk.Frame(self.inventory_notebook, padding=8)
        folders_tab.columnconfigure(0, weight=1)
        folders_tab.rowconfigure(1, weight=1)
        self.inventory_notebook.add(folders_tab, text="Folder map")
        folder_toolbar = ttk.Frame(folders_tab)
        folder_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Button(
            folder_toolbar,
            text="Add selected folder as source",
            command=self.add_selected_folder_source,
        ).pack(side="left")
        ttk.Label(
            folder_toolbar,
            text="Protected folders are listed; enable the checkbox above to scan them.",
        ).pack(side="left", padx=(12, 0))
        self.folder_tree = ttk.Treeview(
            folders_tab,
            columns=("files", "size", "status"),
            show="tree headings",
            selectmode="browse",
        )
        self.folder_tree.heading("#0", text="Drive / folder")
        self.folder_tree.column("#0", width=430, minwidth=190, stretch=True)
        for column, heading, width in (
            ("files", "Files", 80),
            ("size", "Total size", 100),
            ("status", "Status", 145),
        ):
            self.folder_tree.heading(column, text=heading)
            self.folder_tree.column(column, width=width, minwidth=60, stretch=False)
        self.folder_tree.grid(row=1, column=0, sticky="nsew")
        folder_scroll = ttk.Scrollbar(folders_tab, orient="vertical", command=self.folder_tree.yview)
        folder_scroll.grid(row=1, column=1, sticky="ns")
        self.folder_tree.configure(yscrollcommand=folder_scroll.set)
        self.folder_tree.tag_configure("protected", foreground="#d98b2b")
        self.folder_tree.bind("<Double-1>", self.open_selected_folder)



        self._apply_dark_theme()
        self.populate_default_roots()
        self.root.after(50, self._poll_queue)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def _drag_window(self, event: tk.Event) -> None:
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def _start_resize(self, event: tk.Event) -> None:
        self._resize_x = event.x_root
        self._resize_y = event.y_root
        self._resize_w = self.root.winfo_width()
        self._resize_h = self.root.winfo_height()

    def _resize_window(self, event: tk.Event) -> None:
        dx = event.x_root - self._resize_x
        dy = event.y_root - self._resize_y
        new_w = max(self.root.minsize()[0], self._resize_w + dx)
        new_h = max(self.root.minsize()[1], self._resize_h + dy)
        self.root.geometry(f"{int(new_w)}x{int(new_h)}")

    def _resize_root_list(self, event: tk.Event) -> None:
        self.root_list_canvas.itemconfigure(self._root_list_window, width=event.width)

    def _update_root_scrollregion(self, event: tk.Event | None = None) -> None:
        self.root_list_canvas.configure(scrollregion=self.root_list_canvas.bbox("all"))

    def _bind_root_scroll(self, event: tk.Event) -> None:
        self.root.bind_all("<MouseWheel>", self._scroll_root_list)

    def _unbind_root_scroll(self, event: tk.Event) -> None:
        self.root.unbind_all("<MouseWheel>")

    def _scroll_root_list(self, event: tk.Event) -> None:
        self.root_list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _apply_dark_theme(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.dark_bg)
        style.configure("Panel.TFrame", background=self.panel_bg)
        style.configure(
            "TButton",
            background=self.panel_alt,
            foreground=self.text_fg,
            padding=(9, 6),
        )
        style.configure(
            "Primary.TButton",
            background=self.accent,
            foreground="#081321",
            padding=(12, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Danger.TButton",
            background="#8d3c3c",
            foreground=self.text_fg,
            padding=(12, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Hero.TLabel",
            background=self.dark_bg,
            foreground=self.text_fg,
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.dark_bg,
            foreground=self.muted_fg,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background=self.panel_bg,
            foreground=self.text_fg,
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=self.panel_bg,
            foreground=self.muted_fg,
            font=("Segoe UI", 9),
        )
        style.configure(
            "TCheckbutton",
            background=self.panel_bg,
            foreground=self.text_fg,
            padding=(2, 7),
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=self.accent,
            troughcolor=self.panel_alt,
        )
        style.map(
            "TButton",
            background=[("active", self.accent), ("disabled", self.panel_alt)],
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#78b6ff"), ("disabled", self.panel_alt)],
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#aa4b4b"), ("disabled", self.panel_alt)],
        )
        style.map("TCheckbutton", background=[("active", self.panel_alt)])

    def populate_default_roots(self) -> None:
        for widget in self.root_list_frame.winfo_children():
            widget.destroy()
        self.root_vars.clear()
        self.root_entries.clear()

        for root in DEFAULT_ROOTS:
            self.add_root(root, selected=True)
        self._update_selection_summary()

    def add_custom_root(self) -> None:
        directory = filedialog.askdirectory(title="Select folder to add")
        if not directory:
            return

        normalized = Path(directory).resolve().as_posix().replace("\\", "/")
        if normalized in self.root_vars:
            self.root_vars[normalized].set(True)
            return

        self.add_root(normalized, selected=True)

    def choose_destination(self) -> None:
        current = self.destination_var.get().strip()
        options: dict[str, str] = {"title": "Choose archive destination"}
        if current and Path(current).is_dir():
            options["initialdir"] = current
        selected = filedialog.askdirectory(**options)
        if selected:
            self.destination_var.set(Path(selected).as_posix())

    def add_root(self, path: str, *, selected: bool) -> None:
        var = tk.BooleanVar(value=selected)
        var.trace_add("write", self._update_selection_summary)
        self.root_vars[path] = var
        self.root_entries.append(path)

        row = ttk.Frame(self.root_list_frame, style="Panel.TFrame")
        row.pack(fill="x", pady=1)
        ttk.Checkbutton(row, text=path, variable=var).pack(anchor="w", fill="x")
        self._update_root_scrollregion()
        self._update_selection_summary()

    def _update_selection_summary(self, *_args: object) -> None:
        selected_count = len(self.selected_roots())
        total_count = len(self.root_vars)
        self.selection_summary.configure(
            text=f"{selected_count} of {total_count} selected"
        )

    def _set_run_controls(self, *, running: bool) -> None:
        if running:
            self.dry_run_button.state(["disabled"])
            self.execute_button.state(["disabled"])
            self.stop_button.state(["!disabled"])
            self.restart_button.state(["disabled"])
        else:
            self.dry_run_button.state(["!disabled"])
            self.execute_button.state(["!disabled"])
            self.stop_button.state(["disabled"])
            self.restart_button.state(["!disabled"])

    def close_app(self) -> None:
        if not self._is_running:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self.root.destroy()
            return

        if messagebox.askyesno(
            "Run in progress",
            "Cancel the current run and close the organizer?",
            parent=self.root,
        ):
            self._close_when_finished = True
            self.stop_run()

    def selected_roots(self) -> list[str]:
        return [path for path, var in self.root_vars.items() if var.get()]

    def select_all(self) -> None:
        for var in self.root_vars.values():
            var.set(True)

    def clear_all(self) -> None:
        for var in self.root_vars.values():
            var.set(False)

    def set_status(self, text: str, *, color: str, banner: str) -> None:
        self.status_banner.configure(text=banner, bg=color)
        self.progress_label.configure(text=text)
        self.root.update_idletasks()

    def _append_log(self, text: str) -> None:
        print(text, end="", flush=True)

    def clear_log(self) -> None:
        pass

    @staticmethod
    def format_size(size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{size:.0f} B"
            size /= 1024
        return f"{size:.1f} TB"

    def populate_inventory(self, inventory: dict[str, list[dict[str, str | int | bool]]]) -> None:
        self.plan_operations = inventory.get("files", [])
        self.folder_records = inventory.get("folders", [])
        self.checked_plan_items.clear()
        self.refresh_file_rows()
        self.populate_folder_map()
        recommended_count = sum(bool(item.get("auto_recommended")) for item in self.plan_operations)
        large_count = sum(bool(item.get("large")) for item in self.plan_operations)
        protected_source_count = sum(bool(item.get("protected_source")) for item in self.plan_operations)
        protected_count = sum(bool(item.get("protected")) for item in self.folder_records)
        self.file_summary.configure(
            text=(
                f"{len(self.plan_operations)} files found; {recommended_count} recommended; "
                f"{large_count} flagged large; {protected_source_count} from protected folders; "
                f"{protected_count} protected folders skipped."
            )
        )
        self.inventory_notebook.select(0)

    def _is_operation_matching_query(self, operation: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join(
            str(operation.get(key, ""))
            for key in ("category", "source", "target")
        ).casefold()
        source_name = Path(str(operation.get("source", ""))).name.casefold()
        return query in searchable or query in source_name

    def _format_file_row_values_and_tag(
        self, operation: dict, index: int
    ) -> tuple[tuple[str, ...], str]:
        source = Path(str(operation.get("source", "")))
        size_bytes = int(operation.get("size_bytes", 0))
        is_large = bool(operation.get("large"))
        is_protected = bool(operation.get("protected_source"))
        auto_recommended = bool(operation.get("auto_recommended", operation.get("movable", True)))
        include = "Yes" if index in self.checked_plan_items else "No"
        target = str(operation.get("target", "")) or "Not set"
        flag = "Protected" if is_protected else ("Large" if is_large else "")
        tag = "protected" if is_protected else ("large" if is_large else "recommended" if auto_recommended else "other")
        values = (
            include,
            str(operation.get("category", "")),
            source.name,
            self.format_size(size_bytes),
            flag,
            str(source),
            target,
        )
        return values, tag

    def refresh_file_rows(self, *_args: object) -> None:
        if not hasattr(self, "file_tree"):
            return
        query = self.file_filter_var.get().strip().casefold()
        for item_id in self.file_tree.get_children():
            self.file_tree.delete(item_id)
        for index, operation in enumerate(self.plan_operations):
            if not self._is_operation_matching_query(operation, query):
                continue
            values, tag = self._format_file_row_values_and_tag(operation, index)
            self.file_tree.insert(
                "",
                "end",
                iid=f"file-{index}",
                values=values,
                tags=(tag,),
            )
        self.file_tree.tag_configure("protected", foreground="#d98b2b")
        self.file_tree.tag_configure("large", foreground="#f0b35a")
        self.file_tree.tag_configure("other", foreground="#89959a")

    def populate_folder_map(self) -> None:
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.folder_paths.clear()
        row_by_path: dict[str, str] = {}
        records = sorted(
            self.folder_records,
            key=lambda record: (int(record.get("depth", 0)), str(record["path"]).casefold()),
        )
        for index, record in enumerate(records):
            path = str(record["path"])
            path_key = path.casefold()
            parent_path = str(record.get("parent", ""))
            parent_id = row_by_path.get(parent_path.casefold(), "")
            item_id = f"folder-{index}"
            name = Path(path).name or path
            protected = bool(record.get("protected"))
            self.folder_tree.insert(
                parent_id,
                "end",
                iid=item_id,
                text=name,
                values=(
                    record.get("file_count", 0),
                    self.format_size(int(record.get("size_bytes", 0))),
                    "Protected / not scanned" if protected else "Scanned",
                ),
                tags=("protected",) if protected else (),
                open=int(record.get("depth", 0)) == 0,
            )
            row_by_path[path_key] = item_id
            self.folder_paths[item_id] = path

    def toggle_file_selection(self, event: tk.Event) -> str | None:
        if self.file_tree.identify_column(event.x) != "#1":
            return None
        item_id = self.file_tree.identify_row(event.y)
        if not item_id or not item_id.startswith("file-"):
            return None
        index = int(item_id.split("-", 1)[1])
        if index in self.checked_plan_items:
            self.checked_plan_items.remove(index)
        else:
            self.checked_plan_items.add(index)
        self.refresh_file_rows()
        return "break"

    def select_movable_files(self) -> None:
        self.checked_plan_items = {
            index
            for index, operation in enumerate(self.plan_operations)
            if bool(operation.get("auto_recommended", operation.get("movable", True)))
        }
        self.refresh_file_rows()

    def _confirm_include_protected(self) -> None:
        if not self.include_protected_var.get():
            return
        if not messagebox.askyesno(
            "Include protected folders?",
            "The next scan will also look inside named system, install, and game "
            "folders (Windows, Program Files, Steam, etc.). You still choose which "
            "files to move. Continue?",
            parent=self.root,
        ):
            self.include_protected_var.set(False)

    def clear_file_selection(self) -> None:
        self.checked_plan_items.clear()
        self.refresh_file_rows()

    def open_selected_file_location(self, _event: tk.Event | None = None) -> None:
        selection = self.file_tree.selection()
        if not selection:
            return
        index = int(selection[0].split("-", 1)[1])
        folder = Path(str(self.plan_operations[index]["source"])).parent
        self.open_folder_path(folder)

    def open_selected_folder(self, _event: tk.Event | None = None) -> None:
        selection = self.folder_tree.selection()
        if selection:
            self.open_folder_path(Path(self.folder_paths[selection[0]]))

    @staticmethod
    def open_folder_path(folder: Path) -> None:
        if not folder.is_dir():
            return
        if hasattr(os, "startfile"):
            os.startfile(str(folder))

    def add_selected_folder_source(self) -> None:
        selection = self.folder_tree.selection()
        if not selection:
            return
        selected_path = self.folder_paths[selection[0]]
        record = next(
            (item for item in self.folder_records if str(item["path"]).casefold() == selected_path.casefold()),
            None,
        )
        if record and record.get("protected"):
            messagebox.showwarning(
                "Protected folder",
                "Protected system, application, and archive folders cannot be added as scan sources.",
                parent=self.root,
            )
            return
        normalized = Path(selected_path).resolve().as_posix()
        if normalized in self.root_vars:
            self.root_vars[normalized].set(True)
            return
        self.add_root(normalized, selected=True)

    def stop_run(self) -> None:
        if not self._is_running:
            return

        self._cancel_event.set()
        self.stop_button.state(["disabled"])
        self.set_status(
            "Status details: cancelling organizer",
            color=self.warn,
            banner="STATUS: CANCELLING",
        )
        self._append_log("\nCancellation requested...\n")

    def restart_app(self) -> None:
        if self._is_running:
            messagebox.showwarning(
                "Run in progress",
                "Wait for the current run to finish before resetting the organizer.",
                parent=self.root,
            )
            return

        self.populate_default_roots()
        self.clear_log()
        self.progress_bar.configure(value=0)
        self.set_status(
            "Ready when you are.", color=self.success, banner="STATUS: READY"
        )

    def _validate_run_inputs(
        self, execute: bool
    ) -> tuple[bool, str, float, list[str], list[str], list[dict[str, str | int | bool]]]:
        destination = self.destination_var.get().strip()
        if not destination:
            messagebox.showwarning(
                "No destination selected",
                "Choose an archive destination before scanning.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []

        try:
            large_file_mb = float(self.large_file_var.get())
            if large_file_mb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid size threshold",
                "Enter a positive number of megabytes for the large-file flag.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []

        categories = [
            category
            for category, variable in self.category_vars.items()
            if variable.get()
        ]
        if not categories:
            messagebox.showwarning(
                "No categories selected",
                "Select at least one file category before scanning.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []

        roots = self.selected_roots()
        selected_operations = [
            self.plan_operations[index]
            for index in sorted(self.checked_plan_items)
            if index < len(self.plan_operations)
        ]
        if not execute and not roots:
            messagebox.showwarning(
                "No folders selected",
                "Select at least one folder before scanning.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []
        if execute and not selected_operations:
            messagebox.showwarning(
                "No files selected",
                "Select files to move in the Files tab first.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []

        if self._is_running:
            messagebox.showwarning(
                "Run in progress",
                "A housekeeping run is already active.",
                parent=self.root,
            )
            return False, "", 0.0, [], [], []

        return True, destination, large_file_mb, categories, roots, selected_operations

    def run_organizer(self, execute: bool) -> None:
        valid, destination, large_file_mb, categories, roots, selected_operations = (
            self._validate_run_inputs(execute)
        )
        if not valid:
            return

        if execute and not messagebox.askyesno(
            "Confirm file moves",
            f"Move {len(selected_operations)} selected files to {destination}? No files will be deleted.",
            parent=self.root,
        ):
            return

        self._cancel_event.clear()
        self._is_running = True
        self._set_run_controls(running=True)
        self.set_status(
            "Status details: scanning selected folders" if not execute else "Status details: moving selected files",
            color=self.accent,
            banner="STATUS: RUNNING",
        )
        self.progress_bar.configure(value=0)
        self.clear_log()

        self._executor.submit(
            self._worker_execute,
            execute,
            roots,
            destination,
            categories,
            large_file_mb,
            self.include_protected_var.get(),
            selected_operations,
            Path("housekeeping_log.txt"),
        )

    def _worker_execute(
        self,
        execute: bool,
        roots: list[str],
        destination: str,
        categories: list[str],
        large_file_mb: float,
        include_protected: bool,
        selected_operations: list[dict[str, str | int | bool]],
        log_path: Path,
    ) -> None:
        log_lines: list[str] = []

        def log(msg: str) -> None:
            log_lines.append(msg)
            self._work_queue.put(("LOG", msg))

        def progress(current: int, total: int, file_path: str) -> None:
            if self._cancel_event.is_set():
                raise InterruptedError("Cancelled by user")
            self._work_queue.put(("PROGRESS", current, total, file_path))

        try:
            dest_path = Path(destination).expanduser().resolve()
            if not execute:
                log(f"Starting in-process scan across {len(roots)} root folders...\n")
                log(f"Archive destination: {dest_path}\n")
                log(f"Active categories: {', '.join(categories)}\n\n")

                inventory = scan_archive_inventory(
                    [Path(r) for r in roots],
                    destination_root=dest_path,
                    categories=set(categories),
                    large_file_threshold_bytes=int(large_file_mb * 1024 * 1024),
                    include_protected=include_protected,
                    dry_run=True,
                    progress_callback=progress,
                )
                if self._cancel_event.is_set():
                    raise InterruptedError("Cancelled by user")

                self._work_queue.put(("INVENTORY", inventory))
                log(f"\nScan complete: {len(inventory['files'])} planned files mapped in RAM.\n")
                self._work_queue.put(("SUCCESS", "Scan completed successfully."))
            else:
                log(f"Starting native file move for {len(selected_operations)} files...\n")
                total = len(selected_operations)
                moved_results = []
                for index, operation in enumerate(selected_operations, start=1):
                    if self._cancel_event.is_set():
                        raise InterruptedError("Cancelled by user")

                    source = Path(str(operation["source"]))
                    target = Path(str(operation["target"])).resolve()

                    if not source.is_file():
                        log(f"[SKIP] Source missing: {source}\n")
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Collision-safe renaming: {stem}_{counter}{suffix}
                    counter = 1
                    actual_target = target
                    while actual_target.exists():
                        actual_target = target.with_name(f"{target.stem}_{counter}{target.suffix}")
                        counter += 1

                    shutil.move(str(source), str(actual_target))
                    log(f"Moved: {source.name} -> {actual_target}\n")
                    moved_results.append({"source": str(source), "target": str(actual_target)})
                    progress(index, total, str(source))

                self._work_queue.put(("EXECUTE_DONE", moved_results))
                log(f"\nOrganization complete: {len(moved_results)} files moved safely.\n")
                self._work_queue.put(("SUCCESS", f"Successfully moved {len(moved_results)} files."))

        except InterruptedError:
            log("\nHousekeeping operation cancelled by user.\n")
            self._work_queue.put(("CANCELLED", "Operation cancelled by user."))
        except Exception as exc:
            log(f"\nHousekeeping error: {exc}\n")
            self._work_queue.put(("ERROR", str(exc)))
        finally:
            try:
                write_log_file(log_path, "".join(log_lines))
            except Exception:
                pass

    def _handle_queue_progress(self, current: int, total: int, file_path: str) -> None:
        if total > 0:
            percent = min(100, max(0, int((current / total) * 100)))
            self.progress_bar.configure(value=percent)
            self.progress_label.configure(
                text=f"Status details: processing {current} of {total} ({Path(file_path).name})"
            )

    def _handle_queue_execute_done(self, moved_items: list[dict]) -> None:
        moved_sources = {m["source"] for m in moved_items}
        self.plan_operations = [
            op for op in self.plan_operations
            if str(op.get("source")) not in moved_sources
        ]
        self.checked_plan_items.clear()
        self.refresh_file_rows()

    def _handle_queue_terminal_state(self, msg_type: str, message: str) -> None:
        self._is_running = False
        self._set_run_controls(running=False)
        if msg_type == "SUCCESS":
            self.progress_bar.configure(value=100)
            self.set_status(message, color=self.success, banner="STATUS: SUCCESS")
        elif msg_type == "CANCELLED":
            self.set_status(message, color=self.warn, banner="STATUS: CANCELLED")
        elif msg_type == "ERROR":
            self.set_status(f"Error: {message}", color=self.fail, banner="STATUS: FAILED")
        if self._close_when_finished:
            self.root.destroy()

    def _handle_queue_item(self, item: tuple) -> None:
        msg_type = item[0]
        if msg_type == "LOG":
            self._append_log(item[1])
        elif msg_type == "PROGRESS":
            self._handle_queue_progress(item[1], item[2], item[3])
        elif msg_type == "INVENTORY":
            self.populate_inventory(item[1])
        elif msg_type == "EXECUTE_DONE":
            self._handle_queue_execute_done(item[1])
        elif msg_type in {"SUCCESS", "CANCELLED", "ERROR"}:
            self._handle_queue_terminal_state(msg_type, item[1])

    def _poll_queue(self) -> None:
        try:
            while not self._work_queue.empty():
                item = self._work_queue.get_nowait()
                self._handle_queue_item(item)
        except queue.Empty:
            pass

        try:
            self.root.after(50, self._poll_queue)
        except Exception:
            pass


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if len(sys.argv) > 1:
        roots = [Path(r) for r in args.roots]
        dest = Path(args.destination).expanduser().resolve()
        log_lines: list[str] = []

        def cli_progress(cur: int, tot: int, pth: str) -> None:
            pct = int((cur / tot) * 100) if tot > 0 else 0
            print(f"[{pct}%] {cur}/{tot}: {pth}")

        if args.mode == "archive":
            inventory = scan_archive_inventory(
                roots,
                destination_root=dest,
                categories=set(args.categories),
                large_file_threshold_bytes=int(args.large_file_mb * 1024 * 1024),
                include_protected=args.include_protected,
                dry_run=not args.execute,
                progress_callback=cli_progress,
            )
            print(f"\nScan complete: {len(inventory['files'])} planned operations.")
            write_log_file(args.log_file, f"Archived plan for {len(inventory['files'])} files.\n")
        raise SystemExit(0)

    root = tk.Tk()
    app = HousekeepingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
