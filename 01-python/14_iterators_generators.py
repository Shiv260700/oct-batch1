# Iterators and generators: producing values one at a time

import sys
from contextlib import contextmanager
from pathlib import Path

# -----------------------------------------------------
# 1. What a for loop really does
# -----------------------------------------------------

colors = ["red", "green", "blue"]

it = iter(colors)  # get an iterator
print(next(it))    # red
print(next(it))    # green
print(next(it))    # blue
# next(it)         # StopIteration: nothing left; `for` stops here


# -----------------------------------------------------
# 2. Generator function: `yield` instead of `return`
# -----------------------------------------------------

def count_up_to(limit):
    n = 1
    while n <= limit:
        yield n  # pause here and hand back n
        n += 1   # resume here on the next call


for number in count_up_to(3):
    print(number)

gen = count_up_to(2)
print(gen)        # a generator object; nothing has run yet
print(list(gen))  # [1, 2]


# -----------------------------------------------------
# 3. Why generators: lazy, low memory, can be infinite
# -----------------------------------------------------

def fibonacci():
    a, b = 0, 1
    while True:  # infinite, but only computes what you ask for
        yield a
        a, b = b, a + b


fib = fibonacci()
print([next(fib) for _ in range(10)])


# -----------------------------------------------------
# 4. Chaining generators into a pipeline
# -----------------------------------------------------

def read_lines(lines):
    for line in lines:
        yield line.strip()


def non_empty(lines):
    for line in lines:
        if line:
            yield line


raw = ["  apple ", "", " banana", "   ", "cherry  "]
for item in non_empty(read_lines(raw)):
    print(item)


# -----------------------------------------------------
# 5. @contextmanager: a context manager from a generator
# -----------------------------------------------------

@contextmanager
def tag(name):
    print(f"<{name}>")       # like __enter__
    try:
        yield
    finally:
        print(f"</{name}>")  # like __exit__, runs even on errors


with tag("p"):
    print("Hello inside a tag")


# -----------------------------------------------------
# 6. Processing a large file one line at a time
# -----------------------------------------------------

big_file = Path(__file__).parent / "output" / "readings.csv"
big_file.parent.mkdir(exist_ok=True)

with open(big_file, "w") as f:  # make a 200,000-line sample file
    f.write("sensor,value\n")
    for i in range(200_000):
        f.write(f"s{i % 5},{i % 100}\n")


def read_values(path):
    with open(path) as f:
        next(f)  # skip the header
        for line in f:  # the file object is itself a lazy iterator
            _, value = line.rstrip("\n").split(",")
            yield int(value)


def above(values, threshold):
    return (v for v in values if v > threshold)


# Only one line is in memory at any moment
print(sum(above(read_values(big_file), 90)))

# Compare memory: a full list vs a generator
values_list = list(read_values(big_file))
values_gen = read_values(big_file)
print(f"list: {sys.getsizeof(values_list):,} bytes")
print(f"generator: {sys.getsizeof(values_gen):,} bytes")
