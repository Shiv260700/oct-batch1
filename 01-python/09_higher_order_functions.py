# Higher-order functions: take a function and return a new one


def hello():
    print("Hello..")


def with_emoji(func, emoji="☺️"):
    def wrapper():
        func()
        print(emoji)
    return wrapper


def with_auth(func):
    def wrapper():
        print("👮🏻")
        func()
    return wrapper


# Wrap hello twice: auth first, then emoji
with_emoji(with_auth(hello))()
