



# simple context manager example without 'with' statement

class SimpleContextManager:
    def __enter__(self):
        print("Entering context")
        return self

    def f(self):
        print("Inside context method")

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting context")


# way-1: without 'with' statement
cm = SimpleContextManager()
cm.__enter__()
cm.f()
cm.__exit__(None, None, None)

# way-2: using 'with' statement
with SimpleContextManager() as cm:
    cm.f()

# read lunch menu using 'with' statement
with open("lunch-menu.txt", "r") as f:
    content = f.read()
    print(content)