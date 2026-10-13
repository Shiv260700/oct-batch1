# Code under test


def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("can't divide by zero")
    return a / b


def average(values: list[float]) -> float:
    if not values:
        raise ValueError("average of an empty list")
    return sum(values) / len(values)


def word_count(path) -> int:
    with open(path) as f:
        return len(f.read().split())
