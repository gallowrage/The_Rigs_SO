from pathlib import Path
import json
import pytest

from src.python_starter.drive_organizer import (
    _check_duplicate_target,
    _classify_by_extension,
    _classify_by_keywords,
    _execute_file_operation,
    _is_supported_drive_category,
    _print_organizer_results,
    _resolve_archive_target_directory,
    _run_archive_or_organize,
    _validate_archive_categories,
    apply_archive_plan,
    build_parser,
    classify_path,
    choose_unique_destination,
    file_hash,
    is_system_install_path,
    main as organizer_main,
    music_target_dir,
    relative_target_path,
    scan_archive_inventory,
    scan_archive_roots,
    scan_roots,
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


def test_is_system_install_path_and_classifications() -> None:
    assert is_system_install_path(Path("C:/Windows/System32/cmd.exe")) is True
    assert is_system_install_path(Path("C:/Python/Lib/site-packages/pkg/mod.py")) is True
    assert is_system_install_path(Path("D:/Custom/MyFile.txt")) is False

    assert _classify_by_keywords("my photos gallery") == "images"
    assert _classify_by_keywords("unknown folder") is None

    assert _classify_by_extension(Path("clip.mp4"), "clip.mp4") == "videos"
    assert _classify_by_extension(Path("pic.png"), "pic.png") == "images"
    assert _classify_by_extension(Path("song.mp3"), "song.mp3") == "music"
    assert _classify_by_extension(Path("doc.pdf"), "doc.pdf") == "documents"
    assert _classify_by_extension(Path("app.py"), "app.py") == "coding"
    assert _classify_by_extension(Path("driver.sys"), "driver.sys") == "system"
    assert _classify_by_extension(Path("mystery.xyz"), "mystery.xyz") is None

    assert classify_path(Path("D:/Random/mystery.xyz")) == "ignore"


def test_music_target_dir_and_relative_target_path() -> None:
    assert music_target_dir(Path("E:/Raw/Loops/kick.wav")) == Path("E:/Music/Loops_&_Samples")
    assert music_target_dir(Path("E:/Raw/Song.als")) == Path("E:/Music/DAW_Projects")
    assert music_target_dir(Path("E:/Raw/Take1.wav")) == Path("E:/Music/Recordings")
    assert music_target_dir(Path("E:/Raw/Other.dat")) == Path("E:/Music/Audio")

    assert relative_target_path(Path("C:/Downloads/Sub/file.txt")) == Path("Sub/file.txt")
    assert relative_target_path(Path("file.txt")) == Path("file.txt")


def test_target_for_category_and_supported_drive() -> None:
    assert target_for_category("images", Path("E:/Downloads/pic.jpg")) == Path("E:/Photos/pic.jpg")
    assert target_for_category("games", Path("D:/Downloads/steam/game.exe")) == Path("D:/Games/Steam/steam/game.exe")
    assert target_for_category("games", Path("D:/Downloads/indie/game.exe")) == Path("D:/Games/Third_Party/indie/game.exe")
    assert target_for_category("coding", Path("C:/Downloads/main.py")) == Path("C:/Projects/Coding/main.py")
    assert target_for_category("unknown", Path("C:/Downloads/main.py")) == Path("C:/Downloads/main.py")

    assert _is_supported_drive_category(Path("C:/test.py"), "coding") is True
    assert _is_supported_drive_category(Path("D:/game.exe"), "games") is True
    assert _is_supported_drive_category(Path("E:/song.mp3"), "music") is True
    assert _is_supported_drive_category(Path("F:/song.mp3"), "music") is False


def test_file_hash_duplicate_and_execute_file_operation(tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f3 = tmp_path / "c.txt"
    f1.write_text("hello", encoding="utf-8")
    f2.write_text("hello", encoding="utf-8")
    f3.write_text("world", encoding="utf-8")

    h1 = file_hash(f1)
    assert h1 == file_hash(f2)

    target, is_dup = _check_duplicate_target(f2, h1)
    assert is_dup is True
    assert target == f2

    target_diff, is_dup_diff = _check_duplicate_target(f3, h1)
    assert is_dup_diff is False
    assert target_diff != f3

    dry_res = _execute_file_operation(f1, tmp_path / "dest" / "a.txt", dry_run=True)
    assert dry_res["action"] == "move"
    assert f1.exists()

    exec_res = _execute_file_operation(f1, tmp_path / "dest" / "a.txt", dry_run=False)
    assert exec_res["action"] == "moved"
    assert (tmp_path / "dest" / "a.txt").exists()


def test_scan_roots_with_progress_callback(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "scan_src"
    src.mkdir()
    f1 = src / "script.py"
    f2 = src / "script_copy.py"
    f1.write_text("print(1)", encoding="utf-8")
    f2.write_text("print(1)", encoding="utf-8")

    monkeypatch.setattr("src.python_starter.drive_organizer.is_system_install_path", lambda p: False)
    monkeypatch.setattr("src.python_starter.drive_organizer._is_supported_drive_category", lambda p, c: True)
    monkeypatch.setattr("src.python_starter.drive_organizer.target_for_category", lambda c, p: tmp_path / "out" / p.name)

    progress_events = []
    ops = scan_roots([src], dry_run=True, progress_callback=lambda i, t, p: progress_events.append((i, t)))
    assert len(ops) == 2
    assert any(op["action"] == "move" for op in ops)
    assert any(op["action"] == "skip duplicate" for op in ops)
    assert len(progress_events) == 2


def test_validate_archive_categories_and_edge_cases(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown archive categories"):
        _validate_archive_categories({"InvalidCategory"})

    assert _resolve_archive_target_directory("Audio", Path("E:/Master_Archive")) == Path(r"E:\Master_Music_Archive")
    assert _resolve_archive_target_directory("Audio", tmp_path) == tmp_path / "Audio"

    # Test apply_archive_plan error branches
    archive = tmp_path / "archive"
    archive.mkdir()
    outside_target = tmp_path / "outside" / "doc.pdf"
    missing_source = tmp_path / "missing.pdf"

    results = apply_archive_plan(
        [
            {"source": str(missing_source), "target": str(archive / "doc.pdf"), "movable": False},
            {"source": str(missing_source), "target": str(outside_target), "movable": True},
            {"source": str(missing_source), "target": str(archive / "doc.pdf"), "movable": True},
        ],
        destination_root=archive,
    )
    assert results[0]["action"] == "review"
    assert results[1]["action"] == "failed"
    assert "outside" in str(results[1]["error"])
    assert results[2]["action"] == "failed"
    assert "missing" in str(results[2]["error"])


def test_run_archive_or_organize_and_main(tmp_path: Path, monkeypatch, capsys) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "note.pdf").write_text("pdf", encoding="utf-8")
    archive = tmp_path / "archive"
    plan_file = tmp_path / "plan.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "drive_organizer.py",
            "--mode",
            "archive",
            "--roots",
            str(src),
            "--destination",
            str(archive),
            "--plan-output",
            str(plan_file),
        ],
    )
    organizer_main()
    assert plan_file.exists()
    out = capsys.readouterr().out
    assert "Dry run only" in out

    # Test invalid execute-plan JSON error
    bad_plan = tmp_path / "bad.json"
    bad_plan.write_text("{not_json", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(["--mode", "archive", "--execute-plan", str(bad_plan), "--destination", str(archive)])
    with pytest.raises(ValueError, match="Unable to read selected archive plan"):
        _run_archive_or_organize(args, [src], lambda *a: None)

