from __future__ import annotations

import argparse
import sys

from src.python_starter.drive_organizer import main as organizer_main


DEFAULT_ROOTS = [
    "C:/Users",
    "D:/Games",
    "D:/SteamLibrary",
    "E:/Music",
    "E:/Photos",
    "E:/Documents",
    "E:/Master_Archive",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the drive organizer in housekeeping mode. "
            "It scans user-owned folders and moves media, documents, and project files into the configured archive layout."
        )
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=DEFAULT_ROOTS,
        help="Folders to scan. Defaults to the housekeeping roots used by the organizer.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files. Without this flag, the organizer performs a dry run and prints the plan.",
    )
    parser.add_argument(
        "--mode",
        choices=["housekeeping", "organize"],
        default="housekeeping",
        help="Set the organizer mode. Housekeeping is the default and focuses on user-owned data roots.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    args_list = ["drive_organizer.py", "--mode", args.mode]
    if args.execute:
        args_list.append("--execute")
    if args.roots:
        args_list.extend(["--roots", *args.roots])

    sys.argv = args_list
    organizer_main()


if __name__ == "__main__":
    main()
