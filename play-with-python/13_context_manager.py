# Context managers: setup and cleanup with `with`

from pathlib import Path


class SimpleContextManager:
    def __enter__(self):
        print("Entering context")
        return self

    def do_work(self):
        print("Inside context")

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting context")


# Without `with`: call __enter__/__exit__ by hand.
# If do_work() raises, __exit__ is never called.
cm = SimpleContextManager()
cm.__enter__()
cm.do_work()
cm.__exit__(None, None, None)

# With `with`: __exit__ always runs, even on errors
with SimpleContextManager() as cm:
    cm.do_work()

# Built-in example: open() closes the file automatically
menu_path = Path(__file__).parent / "lunch_menu.txt"  # works from any folder
with open(menu_path) as f:
    print(f.read())
