from src.python_starter.cli import build_parser, greet, main


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_custom_name():
    assert greet("Alice") == "Hello, Alice!"


def test_cli_build_parser_and_main(monkeypatch, capsys):
    parser = build_parser()
    args = parser.parse_args(["Rigs"])
    assert args.name == "Rigs"

    monkeypatch.setattr("sys.argv", ["cli.py", "Sovereign"])
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, Sovereign!"

