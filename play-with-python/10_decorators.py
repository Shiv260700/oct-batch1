# Decorators: @ syntax for wrapping functions

import time
from functools import wraps


# -----------------------------------------------------
# 1. Simple decorator
# -----------------------------------------------------

def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"before {func.__name__}")
        result = func(*args, **kwargs)
        print(f"after {func.__name__}")
        return result
    return wrapper


@log_call  # same as: greet = log_call(greet)
def greet():
    print("Hi!")


greet()


# -----------------------------------------------------
# 2. Decorator with arguments (one more level of nesting)
# -----------------------------------------------------

def with_emoji(emoji="☺️"):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            print(emoji)
            return result
        return wrapper
    return decorator


@with_emoji(emoji="😌")  # same as: hello = with_emoji(emoji="😌")(hello)
def hello(name):
    print(f"Hello.. {name}")


hello("Nag")


# -----------------------------------------------------
# 3. Timing functions, and why to use @wraps
# -----------------------------------------------------

print(greet.__name__)  # "wrapper": log_call hid the real name


def timer(func):
    @wraps(func)  # copy func's name and docstring onto wrapper
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


@timer
def slow_sum(n):
    """Add up 0..n-1."""
    return sum(range(n))


print(slow_sum(1_000_000))
print(slow_sum.__name__, "-", slow_sum.__doc__)  # kept, thanks to @wraps


# Decorators stack: the one nearest the function is applied first
@timer
@log_call
def work():
    time.sleep(0.1)


work()  # prints "wrapper took": log_call has no @wraps
