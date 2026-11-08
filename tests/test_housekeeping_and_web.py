from __future__ import annotations

import sys
from unittest.mock import MagicMock

import housekeeping
from src.python_starter import web_app


def test_housekeeping_build_parser_defaults() -> None:
    parser = housekeeping.build_parser()
    args = parser.parse_args([])
    assert args.mode == "housekeeping"
    assert args.execute is False
    assert args.roots == housekeeping.DEFAULT_ROOTS


def test_housekeeping_main_delegates_to_organizer(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(housekeeping, "organizer_main", lambda: called.append(list(sys.argv)))

    housekeeping.main(["--mode", "organize", "--execute", "--roots", "C:/TestRoot"])

    assert len(called) == 1
    assert called[0] == [
        "drive_organizer.py",
        "--mode",
        "organize",
        "--execute",
        "--roots",
        "C:/TestRoot",
    ]


def test_web_app_main_starts_and_closes_server(monkeypatch, capsys) -> None:
    fake_server = MagicMock()
    fake_server.serve_forever.side_effect = KeyboardInterrupt()

    monkeypatch.setattr(web_app, "ThreadingHTTPServer", lambda addr, handler: fake_server)
    web_app.main()

    fake_server.serve_forever.assert_called_once()
    fake_server.server_close.assert_called_once()
    output = capsys.readouterr().out
    assert "Piano Chord Studio is running" in output
    assert "Shutting down Piano Chord Studio." in output
