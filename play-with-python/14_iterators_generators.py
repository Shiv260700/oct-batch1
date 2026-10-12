# Iterators and generators: producing values one at a time

from contextlib import contextmanager

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
