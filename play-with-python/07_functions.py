# Functions: defining, arguments, return values, first-class functions

# -----------------------------------------------------
# 1. Define and call a function
# -----------------------------------------------------

def square(n):
    return n * n


print(square(3))


# -----------------------------------------------------
# 2. Default arguments
# -----------------------------------------------------

def greet(name="Guest"):
    print(f"Hello, {name}!")


greet("Alice")
greet()  # uses the default


# -----------------------------------------------------
# 3. Variable number of arguments (*args)
# -----------------------------------------------------

def multiply(*args):
    result = 1
    for num in args:
        result *= num
    return result


print(multiply(2, 3))
print(multiply(2, 3, 4))
print(multiply(2, 3, 4, 5, 6))


# -----------------------------------------------------
# 4. Keyword arguments (any order)
# -----------------------------------------------------

def introduce(name, age):
    print(f"My name is {name} and I am {age} years old.")


introduce(name="Bob", age=25)
introduce(age=30, name="Charlie")


# -----------------------------------------------------
# 5. Positional and keyword arguments together
# -----------------------------------------------------

def describe_pet(pet_name, animal_type="dog"):
    print(f"I have a {animal_type} named {pet_name}.")


describe_pet("Buddy")
describe_pet("Mittens", animal_type="cat")


# -----------------------------------------------------
# 6. Multiple return values (returned as a tuple)
# -----------------------------------------------------

def get_name_and_age():
    return "Alice", 30


name, age = get_name_and_age()  # unpack the tuple
print(f"Name: {name}, Age: {age}")


# -----------------------------------------------------
# 7. Keyword-only arguments (after *)
# -----------------------------------------------------

def display_info(*, name, age):
    print(f"My name is {name} and I am {age} years old.")


display_info(name="David", age=40)
# display_info("David", 40)  # TypeError: must use keywords


# -----------------------------------------------------
# 8. Scope: where a variable can be seen
# -----------------------------------------------------

count = 0  # global: visible everywhere in this file


def show_local():
    count = 99  # local: a new variable, the global is untouched
    print("local count:", count)


def increment():
    global count  # change the global instead of making a local
    count += 1


show_local()
increment()
print("global count:", count)  # 1


def outer():
    total = 0

    def add(n):
        nonlocal total  # change outer()'s variable
        total += n

    add(5)
    add(10)
    print("total:", total)  # 15


outer()


# -----------------------------------------------------
# 9. Functions are first-class objects
# -----------------------------------------------------

# a) Assign a function to a variable
say_square = square
print(say_square(4))


# b) Pass a function as an argument
def with_banner(func):
    print("🌸🌸🌸🌸🌸🌸🌸🌸")
    func()
    print("🌸🌸🌸🌸🌸🌸🌸🌸")


def greet_in_tamil():
    print("வணக்கம்!")


def greet_in_english():
    print("Hello!")


with_banner(greet_in_tamil)
with_banner(greet_in_english)


# c) Return a function from a function (closure)
# A closure remembers variables from its enclosing scope,
# even after that scope has finished running.
def teach():
    notes = "Some important notes"

    def learn():
        print(f"Learning: {notes}")

    return learn


learn = teach()
learn()  # still sees `notes`
