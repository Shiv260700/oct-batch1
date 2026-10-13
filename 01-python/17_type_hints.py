# Type hints: say what types a function expects and returns
#
# Hints are documentation for people and tools (editors, mypy).
# Python does NOT check them when the code runs.

from dataclasses import dataclass
from typing import Callable, Iterator, Optional, Union

# -----------------------------------------------------
# 1. Variables and functions
# -----------------------------------------------------

name: str = "Alice"
age: int = 30


def greet(name: str, excited: bool = False) -> str:
    return f"Hello, {name}{'!' if excited else '.'}"


def log(message: str) -> None:  # returns nothing
    print(message)


print(greet("Bob", excited=True))
log("done")


# -----------------------------------------------------
# 2. Collections
# -----------------------------------------------------

scores: list[int] = [90, 75, 82]
point: tuple[float, float] = (1.5, 2.0)
tags: set[str] = {"python", "ml"}
ages: dict[str, int] = {"Alice": 30, "Bob": 25}


def average(values: list[float]) -> float:
    return sum(values) / len(values)


print(average([1.0, 2.0, 3.0]))


# -----------------------------------------------------
# 3. Optional and Union
# -----------------------------------------------------

def find_age(people: dict[str, int], name: str) -> Optional[int]:
    """Return the age, or None if the name isn't there."""
    return people.get(name)


def to_text(value: Union[int, float]) -> str:
    return f"{value:.1f}"


print(find_age(ages, "Alice"), find_age(ages, "Zoe"))
print(to_text(3))

# Python 3.10+ shorter form: `int | None` and `int | float`


# -----------------------------------------------------
# 4. Functions as values, generators, aliases
# -----------------------------------------------------

def apply(func: Callable[[int], int], value: int) -> int:
    return func(value)


def count_up(limit: int) -> Iterator[int]:
    yield from range(1, limit + 1)


Matrix = list[list[float]]  # type alias: a readable name for a long type


def first_row(matrix: Matrix) -> list[float]:
    return matrix[0]


print(apply(lambda n: n * 10, 4))
print(list(count_up(3)))
print(first_row([[1.0, 2.0], [3.0, 4.0]]))


# -----------------------------------------------------
# 5. Classes and dataclasses
# -----------------------------------------------------

@dataclass
class Product:
    name: str
    price: float
    in_stock: bool = True


def total(products: list[Product]) -> float:
    return sum(p.price for p in products if p.in_stock)


print(total([Product("pen", 1.5), Product("book", 12.0, in_stock=False)]))


# -----------------------------------------------------
# 6. Hints are not enforced at runtime
# -----------------------------------------------------

print(greet(42))  # runs fine; an editor or `mypy` would flag it
