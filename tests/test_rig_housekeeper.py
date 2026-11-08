from pathlib import Path
import os
import pytest
from rig_housekeeper import (
    CATEGORIES,
    EXCLUSIONS,
    ARCHIVE_PATHS,
    RigHousekeeperApp,
)


def test_categories_coverage():
    assert "Documents" in CATEGORIES
    assert "Images" in CATEGORIES
    assert "Audio" in CATEGORIES
    assert "Video" in CATEGORIES
    assert ".pdf" in CATEGORIES["Documents"]
    assert ".mp3" in CATEGORIES["Audio"]
    assert ".mp4" in CATEGORIES["Video"]


def test_exclusions_contain_critical_system_paths():
    assert "windows" in EXCLUSIONS
    assert "program files" in EXCLUSIONS
    assert "$recycle.bin" in EXCLUSIONS
    assert "steamlibrary" in EXCLUSIONS


def test_archive_paths_defined():
    for category in CATEGORIES:
        assert category in ARCHIVE_PATHS
        assert len(ARCHIVE_PATHS[category]) > 0


def test_filter_excluded_dirs():
    # Mocking basic instance without UI launch
    app = RigHousekeeperApp.__new__(RigHousekeeperApp)
    dirs = ["Windows", "Photos", "AppData", "Projects"]
    
    # Test directory that matches exclusions
    assert app._filter_excluded_dirs(r"C:\Windows\System32", dirs) is True
    assert dirs == []

    # Test clean directory
    clean_dirs = ["Photos", "Windows", "Projects"]
    assert app._filter_excluded_dirs(r"C:\Users\User\Documents", clean_dirs) is False
    assert "Windows" not in clean_dirs
    assert "Photos" in clean_dirs
    assert "Projects" in clean_dirs


def test_resolve_unique_dest_path(tmp_path):
    app = RigHousekeeperApp.__new__(RigHousekeeperApp)
    dest_folder = str(tmp_path / "Archive" / "Documents")
    os.makedirs(dest_folder, exist_ok=True)
    
    file_name = "test_doc.txt"
    first_path = os.path.join(dest_folder, file_name)
    Path(first_path).write_text("existing content", encoding="utf-8")

    unique_path, counter = app._resolve_unique_dest_path(dest_folder, file_name)
    assert counter == 2
    assert unique_path == os.path.join(dest_folder, "test_doc_1.txt")


def test_move_process_and_scan_single_drive(tmp_path, monkeypatch):
    import queue

    import rig_housekeeper

    app = RigHousekeeperApp.__new__(RigHousekeeperApp)
    app.log_queue = queue.Queue()
    app._cancel_flag = False
    app._is_running = False

    monkeypatch.setattr(rig_housekeeper, "EXCLUSIONS", {"windows", "$recycle.bin"})
    archive_docs = tmp_path / "Archive" / "Documents"
    monkeypatch.setitem(ARCHIVE_PATHS, "Documents", str(archive_docs))

    drive_root = tmp_path / "DriveC"
    drive_root.mkdir()
    (drive_root / "notes.pdf").write_text("pdf content", encoding="utf-8")
    (drive_root / "readme.unknown").write_text("skip content", encoding="utf-8")

    # Pre-create collision target for notes_dup.pdf
    archive_docs.mkdir(parents=True, exist_ok=True)
    (archive_docs / "collision.txt").write_text("existing", encoding="utf-8")
    (drive_root / "collision.txt").write_text("new", encoding="utf-8")

    moved, coll, skipped = app._scan_single_drive(str(drive_root))
    assert moved == 2
    assert coll == 1
    assert skipped == 1
    assert (archive_docs / "notes.pdf").exists()
    assert (archive_docs / "collision_1.txt").exists()

    # Non-existent drive
    m_missing, c_missing, s_missing = app._scan_single_drive(str(tmp_path / "NonExistentDrive"))
    assert (m_missing, c_missing, s_missing) == (0, 0, 0)


def test_background_file_worker_and_controls(tmp_path, monkeypatch):
    import queue
    from unittest.mock import MagicMock

    app = RigHousekeeperApp.__new__(RigHousekeeperApp)
    app.log_queue = queue.Queue()
    app._cancel_flag = False
    app._is_running = True
    app.after = MagicMock()
    app.progress_bar = MagicMock()
    app.start_button = MagicMock()
    app.cancel_button = MagicMock()

    drive_root = tmp_path / "EmptyDrive"
    drive_root.mkdir()

    app._background_file_worker([str(drive_root)])
    assert app._is_running is False
    app.after.assert_called_once()

    app._on_worker_finished()
    app.progress_bar.stop.assert_called_once()
    app.start_button.configure.assert_called_with(state="normal")
    app.cancel_button.configure.assert_called_with(state="disabled")

    # Test on_cancel_clicked when running
    app._is_running = True
    app.on_cancel_clicked()
    assert app._cancel_flag is True

