from src.python_starter.cli import greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_custom_name():
    assert greet("Alice") == "Hello, Alice!"
