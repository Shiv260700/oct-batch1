
# Example of a decorator that adds an emoji after the function call

def with_emoji(emoji="☺️"):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            print(emoji)
            return result
        return wrapper
    return decorator


@with_emoji(emoji="😌") # HOF
def hello(name):
    print(f"Helo.. {name}")


hello("Nag")

# Example of a simple logging decorator

def log_call(func):
    def wrapper(*args, **kwargs):
        print("before call")
        result = func(*args, **kwargs)
        print("after call")
        return result
    return wrapper


@log_call
def f1():
    print("f1!")

f1()

@log_call
def f2():
    print("f2!")

f2()
