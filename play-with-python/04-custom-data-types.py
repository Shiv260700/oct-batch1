
# custom data type(s) in python  aka objects

# what is an object?
    # attributes | properties | fields | data | info => state
    # methods | functions | behaviors | actions => behavior
    # address in memory => identity

# obj  => sbi

# class -> person with name and age
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Person(name={self.name}, age={self.age})"

    def say_name(self):
        print(f"My name is {self.name}")

    def say_age(self):
        print(f"My age is {self.age}")

# creating an instance of the Person class
person1 = Person("Alice", 25) # creating an instance of the Person class
print(person1)
print(type(person1))
person1.say_name()
person1.say_age()