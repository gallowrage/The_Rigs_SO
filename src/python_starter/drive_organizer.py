from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path


WINDOWS_SYSTEM_DIRS = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "system32",
    "win32",
    "appdata",
    "$recycle.bin",
    "recovery",
    "perflogs",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".aiff",
    ".aif",
    ".m4a",
    ".ogg",
    ".wma",
    ".mid",
    ".midi",
    ".opus",
}

PLUGIN_AND_DAW_MARKERS = (
    "applied acoustics",
    "ableton",
    "fl studio",
    "reaper",
    "garageband",
    "cubase",
    "logic",
    "pro tools",
    "studio one",
    "plugin",
    "plugins",
    "vst",
    "vst3",
    "aax",
    "aaxplugin",
    "au",
    "component",
    "kontakt",
    "sound bank",
    "soundbank",
    "sample library",
    "samples",
    "presets",
    "preset",
    "instrument",
    "virtual instrument",
    "daw",
    "audio effects",
)

MUSIC_PROJECT_EXTENSIONS = {
    ".als",
    ".flp",
    ".rpp",
    ".cpr",
    ".logicx",
    ".band",
    ".sesx",
    ".song",
    ".vip",
    ".aup",
    ".aup3",
    ".project",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".mpeg",
    ".mpg",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
    ".webm",
    ".flv",
    ".3gp",
    ".3g2",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
    ".webp",
    ".raw",
    ".cr2",
    ".nef",
    ".arw",
    ".dng",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".rtf",
    ".csv",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
    ".json",
    ".xml",
    ".log",
    ".md",
}

CODE_EXTENSIONS = {
    ".py",
    ".ipynb",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".rs",
    ".go",
    ".swift",
    ".php",
    ".rb",
    ".sql",
    ".html",
    ".css",
    ".sass",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".bat",
    ".ps1",
    ".sh",
    ".env",
    ".sln",
    ".csproj",
    ".vcxproj",
    ".gitignore",
    ".dll",
    ".lib",
    ".exe",
    ".zip",
    ".rar",
    ".7z",
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
}

SOFTWARE_EXTENSIONS = {
    ".exe",
    ".msi",
    ".bat",
}

FOLDER_LAYOUT = {
    "C": {
        "system": "C:/System",
        "coding": "C:/Projects/Coding",
        "future": "C:/Projects/Future",
    },
    "D": {
        "games": "D:/Games",
        "steam": "D:/Games/Steam",
        "third_party": "D:/Games/Third_Party",
    },
    "E": {
        "music": "E:/Music",
        "photos": "E:/Photos",
        "documents": "E:/Documents",
        "videos": "E:/Master_Archive/Master_Archive_Videos",
    },
}

DEFAULT_HOUSEKEEPING_ROOTS = [
    "C:/Users",
    "D:/Games",
    "D:/SteamLibrary",
    "E:/Music",
    "E:/Photos",
    "E:/Documents",
    "E:/Master_Archive",
]

SYSTEM_INSTALL_ROOTS = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "appdata\\roaming",
    "recovery",
    "$recycle.bin",
    "system volume information",
    "filehistory",
    "file history",
    "windows.old",
    "everything",
    "appdata",
    "programdata",
}

ARCHIVE_CATEGORY_EXTENSIONS = {
    "Documents": DOCUMENT_EXTENSIONS,
    "Images": IMAGE_EXTENSIONS,
    "Audio": AUDIO_EXTENSIONS | MUSIC_PROJECT_EXTENSIONS,
    "Video": VIDEO_EXTENSIONS,
    "Archives": ARCHIVE_EXTENSIONS,
    "Software": SOFTWARE_EXTENSIONS,
}

DEFAULT_ARCHIVE_PATHS = {
    "Documents": Path(r"E:\Master_Archive\Documents"),
    "Images": Path(r"E:\Master_Archive\Images"),
    "Audio": Path(r"E:\Master_Music_Archive"),
    "Video": Path(r"E:\Master_Video_Archive"),
}

UNCATEGORIZED_LARGE_LABEL = "Large Files"

ARCHIVE_EXCLUDED_DIRECTORY_NAMES = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "system volume information",
    "$recycle.bin",
    "recovery",
    "perflogs",
    "steam library",
    "steamlibrary",
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

APP_INSTALL_EXCLUDE_MARKERS = (
    "site-packages",
    "resources/python",
    "resources\\python",
    "ableton1\\resources",
    "ableton1/resources",
    "python\\lib",
    "python/lib",
)

def is_system_install_path(path: Path) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    path_text = " ".join(lower_parts)

    if any(part in SYSTEM_INSTALL_ROOTS for part in lower_parts):
        print(f"SKIPPED (System Root): {path}")
        return True

    for marker in APP_INSTALL_EXCLUDE_MARKERS:
        if marker in path_text:
            print(f"SKIPPED (App Install Marker '{marker}'): {path}")
            return True

    return False


def _classify_by_keywords(full_text: str) -> str | None:
    if any(marker in full_text for marker in PLUGIN_AND_DAW_MARKERS):
        return "music"
    if any(marker in full_text for marker in ["steam", "steamapps", "epic", "gog", "battle.net", "games", "game install"]):
        return "games"
    if any(marker in full_text for marker in ["master_archive_videos", "videos", "video", "movies", "movie", "clips", "archive videos"]):
        return "videos"
    if any(marker in full_text for marker in ["photos", "pictures", "images", "camera", "photo", "gallery"]):
        return "images"
    if any(marker in full_text for marker in ["music", "audio", "daw", "ableton", "fl studio", "reaper", "garageband", "cubase", "logic", "studio one", "pro tools", "studio"]):
        return "music"
    if any(marker in full_text for marker in ["documents", "document", "docs", "notes", "reports", "manuals", "files", "downloads"]):
        return "documents"
    return None


def _classify_by_extension(path: Path, full_text: str) -> str | None:
    ext = path.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "videos"
    if ext in IMAGE_EXTENSIONS:
        return "images"
    if ext in AUDIO_EXTENSIONS or ext in MUSIC_PROJECT_EXTENSIONS:
        return "music"
    if ext in DOCUMENT_EXTENSIONS:
        return "documents"
    if ext in CODE_EXTENSIONS or any(marker in full_text for marker in ["project", "source", "src", "code", "workspace", "repos", ".git", "github"]):
        return "coding"
    if ext in {".sys", ".dll", ".exe"}:
        return "system"
    return None


def classify_path(path: Path) -> str:
    lower_name = path.name.lower()
    lower_parts = [part.lower() for part in path.parts]
    full_text = " ".join(lower_parts + [lower_name])

    if any(marker in full_text for marker in PLUGIN_AND_DAW_MARKERS):
        return "music"
    if is_system_install_path(path):
        return "ignore"
    if any(part in WINDOWS_SYSTEM_DIRS for part in lower_parts):
        return "system"

    by_kw = _classify_by_keywords(full_text)
    if by_kw:
        return by_kw

    by_ext = _classify_by_extension(path, full_text)
    if by_ext:
        return by_ext

    return "ignore"


def music_target_dir(source_path: Path) -> Path:
    lower_path = source_path.as_posix().lower()

    if any(marker in lower_path for marker in PLUGIN_AND_DAW_MARKERS):
        return Path("E:/Music/Plugins")

    if any(marker in lower_path for marker in ["samples", "loops", "one shots", "one-shots", "drums", "kits", "soundbank", "preset", "presets"]):
        return Path("E:/Music/Loops_&_Samples")

    if source_path.suffix.lower() in MUSIC_PROJECT_EXTENSIONS or any(marker in lower_path for marker in ["ableton", "fl studio", "reaper", "garageband", "cubase", "logic", "studio one", "pro tools", "project", "projects"]):
        return Path("E:/Music/DAW_Projects")

    if source_path.suffix.lower() in AUDIO_EXTENSIONS:
        return Path("E:/Music/Recordings")

    return Path("E:/Music/Audio")


def relative_target_path(source_path: Path) -> Path:
    parts = source_path.parts
    if not parts:
        return Path(source_path.name)

    if len(parts) > 1:
        relative_parts = list(parts[1:])
        generic_root_names = {
            "downloads",
            "desktop",
            "documents",
            "music",
            "photos",
            "pictures",
            "videos",
            "users",
            "home",
        }
        if relative_parts and relative_parts[0].lower() in generic_root_names:
            relative_parts = relative_parts[1:]
        if relative_parts:
            return Path(*relative_parts)

    return Path(source_path.name)


def _resolve_category_base_dir(category: str, source_path: Path, drive_letter: str) -> Path | None:
    if category == "music":
        return music_target_dir(source_path)
    if category in {"images", "documents", "videos"}:
        cat_key = "photos" if category == "images" else category
        return Path(FOLDER_LAYOUT[drive_letter][cat_key])
    if category == "games":
        key = "steam" if "steam" in source_path.as_posix().lower() else "third_party"
        return Path(FOLDER_LAYOUT["D"][key])
    if category in {"coding", "system"}:
        return Path(FOLDER_LAYOUT["C"][category])
    return None


def target_for_category(category: str, source_path: Path) -> Path:
    drive = source_path.anchor.upper().replace("\\", "") or "C:"
    drive_letter = drive[0] if drive else "C"
    base_dir = _resolve_category_base_dir(category, source_path, drive_letter)
    if base_dir is not None:
        return base_dir / relative_target_path(source_path)
    return source_path


def choose_unique_destination(destination: Path, existing_files: list[Path]) -> Path:
    existing_names = {item.name for item in existing_files}
    if not destination.exists() and destination.name not in existing_names:
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    candidate = destination

    while candidate.exists() or candidate.name in existing_names:
        candidate = destination.with_name(f"{stem}_{counter}{suffix}")
        counter += 1

    return candidate


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_files_to_scan(roots: list[Path]) -> list[Path]:
    files_to_scan: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for current, _, file_names in os.walk(root, onerror=lambda _error: None):
            current_path = Path(current)
            for file_name in file_names:
                file_path = current_path / file_name
                if file_path.is_file():
                    files_to_scan.append(file_path)
    return files_to_scan


def _is_supported_drive_category(file_path: Path, category: str) -> bool:
    anchor = file_path.anchor.upper()
    if anchor.startswith("C:") and category in {"system", "coding"}:
        return True
    if anchor.startswith("D:") and category == "games":
        return True
    if anchor.startswith("E:"):
        return category in {"music", "images", "documents", "videos"}
    return False


def _check_duplicate_target(target_path: Path, digest: str) -> tuple[Path, bool]:
    if target_path.exists():
        if digest == file_hash(target_path):
            return target_path, True
        target_path = choose_unique_destination(target_path, list(target_path.parent.rglob("*")))
    return target_path, False


def _execute_file_operation(file_path: Path, target_path: Path, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {
            "action": "move",
            "source": str(file_path),
            "target": str(target_path),
        }
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), str(target_path))
    return {
        "action": "moved",
        "source": str(file_path),
        "target": str(target_path),
    }


def _process_single_scan_file(
    file_path: Path,
    seen_hashes: dict[str, set[str]],
    dry_run: bool,
) -> dict[str, str] | None:
    if not file_path.is_file() or is_system_install_path(file_path):
        return None

    category = classify_path(file_path)
    if category == "ignore" or not _is_supported_drive_category(file_path, category):
        return None

    target_path = target_for_category(category, file_path)
    if file_path.is_relative_to(target_path.parent):
        return None

    digest = file_hash(file_path)
    target_path, is_duplicate = _check_duplicate_target(target_path, digest)
    if is_duplicate or digest in seen_hashes[category]:
        return {
            "action": "skip duplicate",
            "source": str(file_path),
            "target": str(target_path),
        }

    seen_hashes[category].add(digest)
    return _execute_file_operation(file_path, target_path, dry_run)


def scan_roots(
    roots: list[Path],
    *,
    dry_run: bool = True,
    progress_callback: callable | None = None,
) -> list[dict[str, str]]:
    operations: list[dict[str, str]] = []
    seen_hashes: dict[str, set[str]] = defaultdict(set)
    files_to_scan = _collect_files_to_scan(roots)
    total_files = len(files_to_scan)

    for index, file_path in enumerate(files_to_scan, start=1):
        op = _process_single_scan_file(file_path, seen_hashes, dry_run)
        if op is not None:
            operations.append(op)
        if progress_callback is not None:
            progress_callback(index, total_files, str(file_path))

    return operations


def _validate_archive_categories(categories: set[str] | None) -> set[str]:
    selected = categories or set(ARCHIVE_CATEGORY_EXTENSIONS)
    unknown = selected.difference(ARCHIVE_CATEGORY_EXTENSIONS)
    if unknown:
        raise ValueError(f"Unknown archive categories: {', '.join(sorted(unknown))}")
    return selected


def _is_path_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _process_archive_dir_entry(
    current_path: Path,
    root: Path,
    archive_root: Path,
    include_protected: bool,
) -> tuple[dict[str, str | int | bool], bool]:
    try:
        depth = len(current_path.relative_to(root).parts)
    except ValueError:
        depth = 0
    record: dict[str, str | int | bool] = {
        "path": str(current_path),
        "parent": str(current_path.parent) if depth > 0 else "",
        "depth": depth,
        "file_count": 0,
        "size_bytes": 0,
        "protected": False,
    }
    is_protected_root = current_path.name.casefold() in ARCHIVE_EXCLUDED_DIRECTORY_NAMES
    is_archive_root = _is_path_inside(current_path.resolve(), archive_root)
    if is_archive_root:
        record["protected"] = True
        return record, False
    if is_protected_root:
        record["protected"] = True
        if not include_protected:
            return record, False
    return record, True


def _scan_files_in_dir(
    current_path: Path,
    file_names: list[str],
    archive_root: Path,
    folder_record: dict[str, str | int | bool],
    extension_categories: dict[str, str],
    selected_categories: set[str],
    large_file_threshold_bytes: int,
    seen_sources: set[str],
    protected_sources: set[str],
    files_to_scan: list[Path],
) -> None:
    for file_name in file_names:
        source_path = current_path / file_name
        if source_path.is_symlink():
            continue
        try:
            resolved_source = source_path.resolve()
            file_size = source_path.stat().st_size
        except OSError:
            continue
        folder_record["file_count"] = int(folder_record["file_count"]) + 1
        folder_record["size_bytes"] = int(folder_record["size_bytes"]) + file_size
        if _is_path_inside(resolved_source, archive_root):
            continue
        category = extension_categories.get(source_path.suffix.lower())
        if category not in selected_categories:
            category = None
        is_large = file_size >= large_file_threshold_bytes
        if category is None and not is_large:
            continue
        source_key = str(resolved_source).casefold()
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        if bool(folder_record["protected"]):
            protected_sources.add(source_key)
        files_to_scan.append(source_path)


def _filter_walk_child_dirs(
    current_path: Path,
    directory_names: list[str],
    archive_root: Path,
    include_protected: bool,
    folder_records: dict[str, dict[str, str | int | bool]],
    depth: int,
) -> list[str]:
    walk_directories: list[str] = []
    for name in directory_names:
        child_path = current_path / name
        child_key = str(child_path.resolve()).casefold()
        child_is_protected = name.casefold() in ARCHIVE_EXCLUDED_DIRECTORY_NAMES
        child_is_archive = _is_path_inside(child_path.resolve(), archive_root)
        if child_is_archive or (child_is_protected and not include_protected):
            folder_records[child_key] = {
                "path": str(child_path),
                "parent": str(current_path),
                "depth": depth + 1,
                "file_count": 0,
                "size_bytes": 0,
                "protected": True,
            }
        else:
            walk_directories.append(name)
    return walk_directories


def _rollup_folder_metrics(folder_records: dict[str, dict[str, str | int | bool]]) -> None:
    for folder_record in sorted(
        folder_records.values(), key=lambda row: int(row["depth"]), reverse=True
    ):
        parent_path = str(folder_record["parent"])
        parent_key = parent_path.casefold()
        parent_record = folder_records.get(parent_key)
        if parent_record is not None:
            parent_record["file_count"] = int(parent_record["file_count"]) + int(
                folder_record["file_count"]
            )
            parent_record["size_bytes"] = int(parent_record["size_bytes"]) + int(
                folder_record["size_bytes"]
            )


def _resolve_archive_target_directory(effective_category: str, archive_root: Path) -> Path:
    if effective_category in DEFAULT_ARCHIVE_PATHS and archive_root.as_posix().lower() == "e:/master_archive":
        return DEFAULT_ARCHIVE_PATHS[effective_category]
    return archive_root / effective_category


def _build_archive_file_operation(
    source_path: Path,
    archive_root: Path,
    extension_categories: dict[str, str],
    selected_categories: set[str],
    large_file_threshold_bytes: int,
    protected_sources: set[str],
    reserved_destinations: set[str],
    dry_run: bool,
) -> dict[str, str | int | bool] | None:
    try:
        file_size = source_path.stat().st_size
    except OSError:
        return None
    category = extension_categories.get(source_path.suffix.lower())
    if category not in selected_categories:
        category = None
    is_large = file_size >= large_file_threshold_bytes
    protected_source = str(source_path.resolve()).casefold() in protected_sources
    effective_category = category or UNCATEGORIZED_LARGE_LABEL

    target_directory = _resolve_archive_target_directory(effective_category, archive_root)
    destination = target_directory / source_path.name
    counter = 1
    while destination.exists() or str(destination).casefold() in reserved_destinations:
        destination = target_directory / f"{source_path.stem}_{counter}{source_path.suffix}"
        counter += 1
    reserved_destinations.add(str(destination).casefold())

    action = "move"
    if not dry_run:
        target_directory.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination))
        action = "moved"

    return {
        "action": action,
        "category": effective_category,
        "source": str(source_path),
        "target": str(destination),
        "size_bytes": file_size,
        "large": is_large,
        "movable": True,
        "auto_recommended": category is not None and not protected_source,
        "protected_source": protected_source,
    }


def scan_archive_inventory(
    roots: list[Path],
    *,
    destination_root: Path,
    categories: set[str] | None = None,
    large_file_threshold_bytes: int = 1024 * 1024 * 1024,
    include_protected: bool = False,
    dry_run: bool = True,
    progress_callback: callable | None = None,
) -> dict[str, list[dict[str, str | int | bool]]]:
    selected_categories = _validate_archive_categories(categories)
    extension_categories = {
        extension: category
        for category, extensions in ARCHIVE_CATEGORY_EXTENSIONS.items()
        for extension in extensions
    }
    archive_root = destination_root.expanduser().resolve()
    files_to_scan: list[Path] = []
    seen_sources: set[str] = set()
    protected_sources: set[str] = set()
    folder_records: dict[str, dict[str, str | int | bool]] = {}
    seen_folders: set[str] = set()

    for root in roots:
        if not root.is_dir():
            continue
        for current, directory_names, file_names in os.walk(
            root, topdown=True, onerror=lambda _error: None
        ):
            current_path = Path(current)
            current_key = str(current_path.resolve()).casefold()
            if current_key in seen_folders:
                directory_names[:] = []
                continue
            seen_folders.add(current_key)

            folder_record, can_descend = _process_archive_dir_entry(
                current_path, root, archive_root, include_protected
            )
            folder_records[current_key] = folder_record
            if not can_descend:
                directory_names[:] = []
                continue

            _scan_files_in_dir(
                current_path, file_names, archive_root, folder_record,
                extension_categories, selected_categories, large_file_threshold_bytes,
                seen_sources, protected_sources, files_to_scan
            )
            directory_names[:] = _filter_walk_child_dirs(
                current_path, directory_names, archive_root, include_protected,
                folder_records, int(folder_record["depth"])
            )

    _rollup_folder_metrics(folder_records)

    files_to_scan.sort(key=lambda path: str(path).casefold())
    operations: list[dict[str, str | int | bool]] = []
    reserved_destinations: set[str] = set()
    total_files = len(files_to_scan)

    for index, source_path in enumerate(files_to_scan, start=1):
        op = _build_archive_file_operation(
            source_path, archive_root, extension_categories, selected_categories,
            large_file_threshold_bytes, protected_sources, reserved_destinations, dry_run
        )
        if op is not None:
            operations.append(op)
        if progress_callback is not None:
            progress_callback(index, total_files, str(source_path))

    return {
        "files": operations,
        "folders": sorted(
            folder_records.values(), key=lambda row: str(row["path"]).casefold()
        ),
    }


def scan_archive_roots(
    roots: list[Path],
    *,
    destination_root: Path,
    categories: set[str] | None = None,
    large_file_threshold_bytes: int = 1024 * 1024 * 1024,
    include_protected: bool = False,
    dry_run: bool = True,
    progress_callback: callable | None = None,
) -> list[dict[str, str | int | bool]]:
    inventory = scan_archive_inventory(
        roots,
        destination_root=destination_root,
        categories=categories,
        large_file_threshold_bytes=large_file_threshold_bytes,
        include_protected=include_protected,
        dry_run=dry_run,
        progress_callback=progress_callback,
    )
    return inventory["files"]


def apply_archive_plan(
    operations: list[dict[str, str | int | bool]], *, destination_root: Path
) -> list[dict[str, str | int | bool]]:
    archive_root = destination_root.expanduser().resolve()
    results: list[dict[str, str | int | bool]] = []

    for operation in operations:
        result = dict(operation)
        if not operation.get("movable", True):
            result["action"] = "review"
            results.append(result)
            continue

        source = Path(str(operation["source"]))
        target = Path(str(operation["target"])).resolve()
        try:
            target.relative_to(archive_root)
        except ValueError:
            result["action"] = "failed"
            result["error"] = "Destination is outside the selected archive folder."
            results.append(result)
            continue

        if not source.is_file() or source.is_symlink():
            result["action"] = "failed"
            result["error"] = "Source file is missing or is a symbolic link."
            results.append(result)
            continue

        counter = 1
        while target.exists():
            target = target.with_name(f"{Path(str(operation['target'])).stem}_{counter}{target.suffix}")
            counter += 1
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
        except OSError as error:
            result["action"] = "failed"
            result["error"] = str(error)
        else:
            result["action"] = "moved"
            result["target"] = str(target)
        results.append(result)

    return results


def safe_console_text(value: object, *, encoding: str | None = None) -> str:
    text = str(value)
    target_encoding = (encoding or sys.stdout.encoding or "utf-8").lower()
    try:
        text.encode(target_encoding, errors="strict")
        return text
    except (LookupError, UnicodeEncodeError):
        fallback = "cp1252" if "cp1252" in target_encoding else "utf-8"
        return text.encode(fallback, errors="replace").decode(fallback)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Organize files across C, D, and E drives using category rules and duplicate hashing."
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=DEFAULT_HOUSEKEEPING_ROOTS,
        help="Folders to scan. Defaults to the housekeeping/user-owned data roots instead of system install directories.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files instead of printing a dry-run plan.",
    )
    parser.add_argument(
        "--mode",
        choices=["housekeeping", "organize", "archive"],
        default="housekeeping",
        help="Use archive mode to sort supported files into Documents, Images, Audio, and Video folders under --destination.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("E:/Master_Archive"),
        help="Base folder for archive mode category folders.",
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=sorted(ARCHIVE_CATEGORY_EXTENSIONS),
        default=sorted(ARCHIVE_CATEGORY_EXTENSIONS),
        help="Categories to include in archive mode.",
    )
    parser.add_argument(
        "--large-file-mb",
        type=float,
        default=1024,
        help="Flag files at or above this size for review. Default: 1024 MB.",
    )
    parser.add_argument(
        "--include-protected",
        action="store_true",
        help="Also scan named system, install, and game folders normally skipped in archive mode.",
    )
    parser.add_argument(
        "--plan-output",
        type=Path,
        help="Write archive preview records as JSON to this path.",
    )
    parser.add_argument(
        "--execute-plan",
        type=Path,
        help="Move only the selected operations from an archive JSON plan.",
    )
    return parser


def _run_archive_or_organize(args, roots: list[Path], emit_progress: callable) -> tuple[list[dict], dict]:
    if args.mode == "archive" and args.execute_plan:
        try:
            selected_operations = json.loads(args.execute_plan.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Unable to read selected archive plan: {error}")
        results = apply_archive_plan(selected_operations, destination_root=args.destination)
        return results, {"files": results, "folders": []}

    if args.mode == "archive":
        inventory = scan_archive_inventory(
            roots,
            destination_root=args.destination,
            categories=set(args.categories),
            large_file_threshold_bytes=int(args.large_file_mb * 1024 * 1024),
            include_protected=args.include_protected,
            dry_run=not args.execute,
            progress_callback=emit_progress,
        )
        return inventory["files"], inventory

    results = scan_roots(roots, dry_run=not args.execute, progress_callback=emit_progress)
    return results, {"files": results, "folders": []}


def _print_organizer_results(results: list[dict], is_execute: bool) -> None:
    for result in results:
        target = f" -> {result['target']}" if result.get("target") else ""
        detail = f" ({result['error']})" if result.get("error") else ""
        print(safe_console_text(f"{result['action']}: {result['source']}{target}{detail}"))

    if not is_execute:
        print(safe_console_text("\nDry run only. Re-run with --execute to physically move files."))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    roots = [Path(root) for root in args.roots]
    if args.mode == "organize" and not args.roots:
        roots = [Path("C:/"), Path("D:/"), Path("E:/")]

    def emit_progress(current: int, total: int, file_path: str) -> None:
        if total <= 0:
            return
        percent = min(100, max(0, int((current / total) * 100)))
        print(safe_console_text(f"PROGRESS {current}/{total} ({percent}%) {file_path}"))

    try:
        results, inventory = _run_archive_or_organize(args, roots, emit_progress)
    except ValueError as err:
        parser.error(str(err))

    if args.plan_output:
        args.plan_output.parent.mkdir(parents=True, exist_ok=True)
        args.plan_output.write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    _print_organizer_results(results, args.execute)


if __name__ == "__main__":
    main()
