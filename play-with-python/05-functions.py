
# python function(s)

#-----------------------------------------------------
#1. how to define function ?
#-----------------------------------------------------

from os import name


def square(n1):
    n3 = n1 * n1
    return n3

# calling the function
result = square(3)
print(result)

#-----------------------------------------------------
#2. how to define function with default arguments?
#-----------------------------------------------------

def greet(name="Guest"):
    print(f"Hello, {name}!")

# calling the function with and without default argument
greet("Alice")
greet()


#-----------------------------------------------------
#3. how to define function with variable number of arguments?
#-----------------------------------------------------

def multiply(*args):
    result = 1
    for num in args:
        result *= num
    return result

# calling the function with different number of arguments
print(multiply(2, 3))
print(multiply(2, 3, 4))
print(multiply(2, 3, 4, 5))
print(multiply(2, 3, 4, 5, 6))


#-----------------------------------------------------
#4. how to define function with keyword arguments?
#-----------------------------------------------------

def introduce(name, age):
    print(f"My name is {name} and I am {age} years old.")

# calling the function with keyword arguments
introduce(name="Bob", age=25)
introduce(age=30, name="Charlie")


#-----------------------------------------------------
#5. how to define function with both positional and keyword arguments?
#-----------------------------------------------------

def describe_pet(pet_name, animal_type="dog"):
    print(f"I have a {animal_type} named {pet_name}.")

# calling the function with both positional and keyword arguments
describe_pet("Buddy")
describe_pet("Mittens", animal_type="cat")

#-----------------------------------------------------
#6. how to define function with return value?
#-----------------------------------------------------

def print_square(n):
    return n * n

v=print_square(4)
print(v)


#-----------------------------------------------------
#7. how to define function with multiple return values?
#-----------------------------------------------------

def get_name_and_age():
    name = "Alice"
    age = 30
    return name, age

# calling the function and unpacking the return values
name, age = get_name_and_age()
print(f"Name: {name}, Age: {age}")


#-----------------------------------------------------
#8. how to define function with keyword-only arguments?
#-----------------------------------------------------

def display_info(*, name, age):
    print(f"My name is {name} and I am {age} years old.")

# calling the function with keyword-only arguments
display_info(name="David", age=40)
display_info(age=35, name="Eve")


#-----------------------------------------------------
#9. principles of function
#-----------------------------------------------------

# - function can be assigned to a variable
# - function can be passed as an argument to another function
# - function can be returned from another function


# - function can be assigned to a variable

def greet(name):
    return f"Hello, {name}!"

# assigning the function to a variable
say_hello = greet
print(say_hello("Alice"))

# - function can be passed as an argument to another function

def greet_with_banner(func):
    print("🌸🌸🌸🌸🌸🌸🌸🌸")
    func()
    print("🌸🌸🌸🌸🌸🌸🌸🌸")


def greet_in_tamil():
    print("வணக்கம்!")


greet_with_banner(greet_in_tamil)

def greet_in_english():
    print("Hello!")

greet_with_banner(greet_in_english)


# - function can be returned from another function

# closure
# A closure is a function object that remembers values in enclosing scopes even if they are not present in memory.
def teach():
    print("Teaching...")
    notes = "Some important notes"
    def learn():
        print("Learning...")
        print(notes)
        print("teaching Ends..")
    print("Teaching Ends")
    return learn

learn = teach()
learn()


#-----------------------------------------------------
#10. summary
#-----------------------------------------------------

# - functions are defined using the 'def' keyword
# - functions can have parameters and return values
# - functions can be assigned to variables
# - functions can be passed as arguments to other functions
# - functions can be returned from other functions (closures)