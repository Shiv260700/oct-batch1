# Testing with pytest
#
# Run from the repo root:
#   python3 -m pytest play-with-python/20_testing_with_pytest -v
#
# pytest finds files named test_*.py and runs every function named test_*.
# A plain `assert` is all you need; pytest shows the values when one fails.

import pytest

from calculator import add, average, divide, word_count

# -----------------------------------------------------
# 1. Basic tests
# -----------------------------------------------------

def test_add():
    assert add(2, 3) == 5


def test_add_floats():
    assert add(0.1, 0.2) == pytest.approx(0.3)  # floats aren't exact


# -----------------------------------------------------
# 2. Testing that errors are raised
# -----------------------------------------------------

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)


def test_average_empty_message():
    with pytest.raises(ValueError, match="empty"):  # check the message too
        average([])


# -----------------------------------------------------
# 3. parametrize: one test, many inputs
# -----------------------------------------------------

@pytest.mark.parametrize("a, b, expected", [
    (10, 2, 5),
    (9, 3, 3),
    (-8, 2, -4),
    (1, 4, 0.25),
])
def test_divide(a, b, expected):
    assert divide(a, b) == expected


# -----------------------------------------------------
# 4. Fixtures: reusable setup
# -----------------------------------------------------

@pytest.fixture
def scores():
    return [80, 90, 100]  # each test gets a fresh copy


def test_average(scores):
    assert average(scores) == 90


def test_average_after_append(scores):
    scores.append(50)
    assert average(scores) == 80


# tmp_path is a built-in fixture: a fresh temporary folder per test
def test_word_count(tmp_path):
    file = tmp_path / "notes.txt"
    file.write_text("one two three")
    assert word_count(file) == 3
