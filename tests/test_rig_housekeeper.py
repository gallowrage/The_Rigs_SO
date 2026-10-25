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


def test_filter_excluded_dirs(monkeypatch):
    monkeypatch.setenv("DISPLAY", "")
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
