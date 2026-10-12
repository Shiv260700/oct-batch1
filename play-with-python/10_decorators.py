# Decorators: @ syntax for wrapping functions


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
