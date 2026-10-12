

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




