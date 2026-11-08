import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from housekeeping_app import HousekeepingApp, build_command, build_parser, write_log_file
from src.python_starter.drive_organizer import safe_console_text


@pytest.fixture
def root() -> tk.Tk:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter is unavailable in this environment.")
    try:
        yield root
    finally:
        root.destroy()


def test_parser_defaults_to_housekeeping_mode_and_dry_run() -> None:
    args = build_parser().parse_args([])

    assert args.mode == "housekeeping"
    assert args.execute is False
    assert args.roots


def test_safe_console_text_handles_windows_unsupported_chars() -> None:
    text = "E:/Music/♫/song.mp3"

    rendered = safe_console_text(text, encoding="cp1252")

    assert isinstance(rendered, str)
    rendered.encode("cp1252", "strict")


def test_housekeeping_app_creates_custom_title_bar(root: tk.Tk) -> None:
    app = HousekeepingApp(root)
    assert hasattr(app, "title_bar")
    assert app.title_bar.winfo_exists()
    assert app.title_bar_title.cget("text") == "File Organizer"
    assert app.close_button.cget("text") == "✕"
    assert hasattr(app, "resize_handle")
    assert app.resize_handle.winfo_exists()


def test_housekeeping_app_summarizes_folder_selection(root: tk.Tk) -> None:
    app = HousekeepingApp(root)
    assert (
        app.selection_summary.cget("text")
        == f"{len(app.root_vars)} of {len(app.root_vars)} selected"
    )


def test_archive_command_uses_selected_destination_categories_and_threshold() -> None:
    args = build_parser().parse_args(
        [
            "--mode",
            "archive",
            "--roots",
            "C:/Users/test/Downloads",
            "--destination",
            "E:/Master Archive",
            "--categories",
            "Audio",
            "Video",
            "--large-file-mb",
            "512",
        ]
    )

    command = build_command(args)

    assert "--mode" in command and command[command.index("--mode") + 1] == "archive"
    assert command[command.index("--destination") + 1] == "E:/Master Archive"
    assert command[command.index("--categories") + 1 : command.index("--large-file-mb")] == [
        "Audio",
        "Video",
    ]
    assert command[command.index("--large-file-mb") + 1] == "512.0"


def test_inventory_views_accept_folder_and_file_records(root: tk.Tk, tmp_path) -> None:
    app = HousekeepingApp(root)
    source = tmp_path / "Downloads"
    protected = source / "Windows"
    app.populate_inventory(
        {
            "files": [
                {
                    "category": "Documents",
                    "source": str(source / "notes.pdf"),
                    "target": str(tmp_path / "Archive" / "Documents" / "notes.pdf"),
                    "size_bytes": 20,
                    "large": False,
                    "movable": True,
                }
            ],
            "folders": [
                {
                    "path": str(source),
                    "parent": "",
                    "depth": 0,
                    "file_count": 1,
                    "size_bytes": 20,
                    "protected": False,
                },
                {
                    "path": str(protected),
                    "parent": str(source),
                    "depth": 1,
                    "file_count": 0,
                    "size_bytes": 0,
                    "protected": True,
                },
            ],
        }
    )

    assert len(app.file_tree.get_children()) == 1
    assert len(app.folder_tree.get_children()) == 1
    protected_item = app.folder_tree.get_children()[0]
    assert app.folder_tree.get_children(protected_item)

    app.clear_all()
    assert (
        app.selection_summary.cget("text") == f"0 of {len(app.root_vars)} selected"
    )

    app.select_all()
    assert (
        app.selection_summary.cget("text")
        == f"{len(app.root_vars)} of {len(app.root_vars)} selected"
    )


def test_format_size_and_write_log_file(tmp_path: Path) -> None:
    assert HousekeepingApp.format_size(512) == "512 B"
    assert HousekeepingApp.format_size(2048) == "2.0 KB"
    assert HousekeepingApp.format_size(5 * 1024 * 1024) == "5.0 MB"

    log_file = tmp_path / "logs" / "out.txt"
    returned = write_log_file(log_file, "test log line\n")
    assert returned == log_file
    assert log_file.read_text(encoding="utf-8") == "test log line\n"


def test_filtering_selection_and_validation(root: tk.Tk, tmp_path: Path, monkeypatch) -> None:
    app = HousekeepingApp(root)
    f1 = tmp_path / "doc.pdf"
    f2 = tmp_path / "big.iso"
    f1.write_text("pdf", encoding="utf-8")
    f2.write_text("iso", encoding="utf-8")

    app.populate_inventory(
        {
            "files": [
                {
                    "category": "Documents",
                    "source": str(f1),
                    "target": str(tmp_path / "Archive" / "doc.pdf"),
                    "size_bytes": 100,
                    "large": False,
                    "movable": True,
                    "auto_recommended": True,
                },
                {
                    "category": "Large Files",
                    "source": str(f2),
                    "target": str(tmp_path / "Archive" / "big.iso"),
                    "size_bytes": 10_000_000,
                    "large": True,
                    "movable": True,
                    "auto_recommended": False,
                },
            ],
            "folders": [],
        }
    )

    app.select_movable_files()
    assert app.checked_plan_items == {0}

    app.file_filter_var.set("big.iso")
    assert len(app.file_tree.get_children()) == 1

    app.file_filter_var.set("")
    assert len(app.file_tree.get_children()) == 2

    app.clear_file_selection()
    assert len(app.checked_plan_items) == 0

    # Validation checks
    warnings = []
    monkeypatch.setattr("housekeeping_app.messagebox.showwarning", lambda title, msg, **kw: warnings.append(title))

    app.large_file_var.set("-5")
    assert app._parse_large_file_mb() is None
    assert "Invalid size threshold" in warnings

    app.large_file_var.set("512")
    assert app._parse_large_file_mb() == 512.0

    # Execute without selected files
    valid, *_ = app._validate_run_inputs(execute=True)
    assert valid is False
    assert "No files selected" in warnings


def test_execute_selected_moves_and_queue_handlers(root: tk.Tk, tmp_path: Path) -> None:
    app = HousekeepingApp(root)
    src = tmp_path / "move_me.txt"
    src.write_text("move content", encoding="utf-8")
    dest = tmp_path / "Archive" / "Documents" / "move_me.txt"

    logs = []
    prog = []
    results = app._execute_selected_moves(
        [{"source": str(src), "target": str(dest)}],
        log_fn=logs.append,
        progress_fn=lambda c, t, p: prog.append((c, t)),
    )
    assert len(results) == 1
    assert dest.exists()
    assert not src.exists()
    assert prog == [(1, 1)]

    # Test queue handlers
    app._handle_queue_item(("PROGRESS", 1, 2, str(dest)))
    assert int(app.progress_bar["value"]) == 50

    app.plan_operations = [{"source": str(dest), "target": str(dest)}]
    app._handle_queue_item(("EXECUTE_DONE", [{"source": str(dest), "target": str(dest)}]))
    assert app.plan_operations == []

    app._handle_queue_item(("SUCCESS", "Done!"))
    assert app._is_running is False
    assert app.status_banner.cget("text") == "STATUS: SUCCESS"

