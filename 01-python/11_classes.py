# Classes: custom data types with state and behavior

from dataclasses import dataclass

# An object has:
#   state    -> attributes (data)
#   behavior -> methods (actions)
#   identity -> its address in memory

# -----------------------------------------------------
# 1. Defining a class
# -----------------------------------------------------

class Person:
    species = "human"  # class attribute: shared by all instances

    def __init__(self, name, age):
        self.name = name  # instance attributes: one per object
        self.age = age

    def __str__(self):
        return f"Person(name={self.name}, age={self.age})"

    def say_name(self):
        print(f"My name is {self.name}")

    def have_birthday(self):
        self.age += 1


person = Person("Alice", 25)
print(person)
print(type(person))
person.say_name()
person.have_birthday()
print(person.age, person.species)

other = Person("Alice", 26)
print(person is other)  # False: different objects (identity)


# -----------------------------------------------------
# 2. Inheritance: reuse and extend a parent class
# -----------------------------------------------------

class Student(Person):
    def __init__(self, name, age, school):
        super().__init__(name, age)  # let Person set name and age
        self.school = school

    def say_name(self):  # override the parent's method
        print(f"I'm {self.name} from {self.school}")


student = Student("Bob", 20, "MIT")
student.say_name()
student.have_birthday()  # inherited from Person
print(student.age)
print(isinstance(student, Person))  # True


# -----------------------------------------------------
# 3. Special (dunder) methods: hook into Python syntax
# -----------------------------------------------------

class Cart:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def __len__(self):           # len(cart)
        return len(self.items)

    def __contains__(self, item):  # item in cart
        return item in self.items

    def __repr__(self):          # shown in the console and in lists
        return f"Cart({self.items})"


cart = Cart()
cart.add("apple")
cart.add("bread")
print(len(cart), "apple" in cart, cart)


# -----------------------------------------------------
# 4. @property: a method that reads like an attribute
# -----------------------------------------------------

class Circle:
    def __init__(self, radius):
        self.radius = radius

    @property
    def area(self):
        return 3.14159 * self.radius ** 2


circle = Circle(2)
print(circle.area)  # no () needed


# -----------------------------------------------------
# 5. @dataclass: writes __init__, __repr__ and __eq__ for you
# -----------------------------------------------------

@dataclass
class Point:
    x: int
    y: int = 0  # default value


p1 = Point(1, 2)
p2 = Point(1, 2)
print(p1)        # Point(x=1, y=2)
print(p1 == p2)  # True: compares values, not identity


# -----------------------------------------------------
# 6. __call__ and the PyTorch pattern
# -----------------------------------------------------

# PyTorch models subclass nn.Module: set up parts in __init__,
# write the computation in forward(), then call the object like a function.
# This mini version shows how that works.

class Module:
    def __call__(self, x):  # model(x) runs this
        return self.forward(x)

    def forward(self, x):
        raise NotImplementedError("subclasses must define forward()")


class Scale(Module):
    def __init__(self, factor):
        self.factor = factor

    def forward(self, x):
        return [value * self.factor for value in x]


class AddBias(Module):
    def __init__(self, bias):
        self.bias = bias

    def forward(self, x):
        return [value + self.bias for value in x]


class Sequential(Module):
    def __init__(self, *layers):
        self.layers = layers

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)  # each layer is callable
        return x


model = Sequential(Scale(2), AddBias(1))
print(model([1, 2, 3]))  # [3, 5, 7]
