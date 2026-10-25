from pathlib import Path

from src.python_starter.drive_organizer import (
    apply_archive_plan,
    build_parser,
    classify_path,
    choose_unique_destination,
    scan_archive_inventory,
    scan_archive_roots,
    target_for_category,
)


def test_classify_path_for_music_and_video() -> None:
    assert classify_path(Path("E:/Music/Productions/Track.wav")) == "music"
    assert classify_path(Path("D:/Downloads/Applied Acoustics Systems/Strings/violin.wav")) == "music"
    assert classify_path(Path("D:/Downloads/Applied Acoustics Systems/Strings/artwork.png")) == "music"
    assert classify_path(Path("E:/Master_Archive/Master_Archive_Videos/clip.mp4")) == "videos"
    assert classify_path(Path("D:/SteamLibrary/SteamApps/common/Game/folder.exe")) == "games"
    assert classify_path(Path("C:/Users/User/Desktop/notes.txt")) == "documents"


def test_preserves_nested_folder_structure_under_umbrella() -> None:
    source = Path("D:/Downloads/Applied Acoustics Systems/Strings/violin.wav")
    target = Path("E:/Music/Plugins/Applied Acoustics Systems/Strings/violin.wav")

    result = target_for_category("music", source)

    assert result == target


def test_filehistory_is_skipped_as_system_backup_content() -> None:
    source = Path("C:/Users/User/Documents/FileHistory/Backup/Project/track.wav")

    assert classify_path(source) == "ignore"


def test_choose_unique_destination_renames_conflicting_file() -> None:
    destination = Path("E:/Media/Documents/report.pdf")
    existing = [destination]

    result = choose_unique_destination(destination, existing)

    assert result != destination
    assert result.name.startswith("report")
    assert result.suffix == ".pdf"


def test_housekeeping_parser_defaults_to_housekeeping_mode() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.mode == "housekeeping"
    assert args.execute is False


def test_archive_inventory_records_folder_map_and_flags_large_files(tmp_path: Path) -> None:
    source = tmp_path / "drive"
    nested = source / "Projects" / "Sessions"
    protected = source / "Windows"
    archive = source / "Master_Archive"
    nested.mkdir(parents=True)
    protected.mkdir()
    archive.mkdir()
    (source / "report.pdf").write_text("document", encoding="utf-8")
    (nested / "song.mp3").write_text("audio", encoding="utf-8")
    (source / "disk-image.bin").write_bytes(b"large file")
    (protected / "protected.pdf").write_text("system", encoding="utf-8")
    (archive / "already-sorted.pdf").write_text("archive", encoding="utf-8")

    inventory = scan_archive_inventory(
        [source],
        destination_root=archive,
        large_file_threshold_bytes=5,
    )

    categories = {operation["category"] for operation in inventory["files"]}
    folder_paths = {record["path"]: record for record in inventory["folders"]}
    assert categories == {"Documents", "Audio", "Large Files"}
    assert any(Path(record["path"]).name == "Sessions" for record in inventory["folders"])
    assert folder_paths[str(protected)]["protected"] is True
    assert folder_paths[str(archive)]["protected"] is True
    assert folder_paths[str(source)]["file_count"] == 3
    large_file = next(
        operation
        for operation in inventory["files"]
        if operation["category"] == "Large Files"
    )
    assert large_file["large"] is True
    assert large_file["movable"] is True
    assert large_file["auto_recommended"] is False
    assert not (archive / "Documents" / "report.pdf").exists()


def test_archive_inventory_can_opt_into_protected_folders(tmp_path: Path) -> None:
    source = tmp_path / "drive"
    protected = source / "Windows"
    protected.mkdir(parents=True)
    (protected / "protected.pdf").write_text("system", encoding="utf-8")
    archive = source / "Master_Archive"
    archive.mkdir()

    skipped = scan_archive_inventory([source], destination_root=archive)
    assert skipped["files"] == []

    included = scan_archive_inventory(
        [source], destination_root=archive, include_protected=True
    )
    protected_file = next(
        operation for operation in included["files"] if operation["category"] == "Documents"
    )
    assert protected_file["protected_source"] is True
    assert protected_file["auto_recommended"] is False
    assert protected_file["movable"] is True


def test_archive_apply_moves_only_selected_plan_entries(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "report.pdf"
    audio = source / "song.mp3"
    document.write_text("document", encoding="utf-8")
    audio.write_text("audio", encoding="utf-8")
    archive = tmp_path / "archive"
    plan = scan_archive_roots(
        [source], destination_root=archive, categories={"Documents", "Audio"}
    )
    selected = [next(operation for operation in plan if operation["category"] == "Documents")]

    result = apply_archive_plan(selected, destination_root=archive)

    assert result[0]["action"] == "moved"
    assert (archive / "Documents" / "report.pdf").read_text(encoding="utf-8") == "document"
    assert audio.exists()
