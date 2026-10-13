# A small module imported by 15_modules_and_imports.py

DEFAULT_NAME = "friend"


def say_hello(name=DEFAULT_NAME):
    return f"Hello, {name}!"


def say_bye(name=DEFAULT_NAME):
    return f"Goodbye, {name}!"


# Runs only when this file is run directly, not when imported
if __name__ == "__main__":
    print(say_hello("tester"))
