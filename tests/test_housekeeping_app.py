import tkinter as tk

import pytest

from housekeeping_app import HousekeepingApp, build_command, build_parser
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
