
def hello():
    print("Hello..")

def hi():
    print("Hi..")

def hey():
    print("Hey..")

# Higher Order Function (HOF)
def with_emoji(func,emoji="☺️"):
    def wrapper():
        func()
        print(emoji)
    return wrapper

def with_auth(func):
    def wrapper():
        print("👮🏻")
        func()
    return wrapper


with_emoji(with_auth(hello))()