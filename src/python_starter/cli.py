import argparse


def greet(name: str = "world") -> str:
    return f"Hello, {name}!"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A tiny starter CLI app.")
    parser.add_argument(
        "name",
        nargs="?",
        default="world",
        help="Name to greet.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(greet(args.name))


if __name__ == "__main__":
    main()
