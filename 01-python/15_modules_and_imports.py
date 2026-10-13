# Modules and imports: reuse code from other files

# -----------------------------------------------------
# 1. Importing from the standard library
# -----------------------------------------------------

import math                       # import the whole module
from random import choice         # import one name
from datetime import date as dt   # import with an alias

print(math.sqrt(16), math.pi)
print(choice(["heads", "tails"]))
print(dt.today())


# -----------------------------------------------------
# 2. Importing your own module (greetings.py, same folder)
# -----------------------------------------------------

import greetings
from greetings import say_bye

print(greetings.say_hello("Alice"))
print(say_bye())
print(greetings.DEFAULT_NAME)

# Note: file names starting with a digit (like this one) can't be imported.
# That's why the reusable code lives in greetings.py.


# -----------------------------------------------------
# 3. __name__ == "__main__"
# -----------------------------------------------------

# Every module has a __name__.
#   Run directly -> "__main__"
#   Imported     -> the module's name ("greetings")
print(__name__)            # __main__
print(greetings.__name__)  # greetings


def main():
    print("Running as a script")


if __name__ == "__main__":
    main()


# -----------------------------------------------------
# 4. Exploring a module
# -----------------------------------------------------

print([name for name in dir(greetings) if not name.startswith("_")])
help(greetings.say_hello)
