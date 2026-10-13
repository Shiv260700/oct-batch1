# Data types: simple values and built-in collections

# -----------------------------------------------------
# 1. Simple data types
# -----------------------------------------------------

name = "Alice"     # str: text
age = 25           # int: whole number
height = 5.6       # float: decimal number
is_student = True  # bool: True or False
result = None      # NoneType: no value

print(type(name))
print(type(age))
print(type(height))
print(type(is_student))
print(type(result))

print(10 + 10)      # 20: numbers add
print("10" + "10")  # "1010": strings join


# -----------------------------------------------------
# 2. Collections (data structures)
# -----------------------------------------------------

# list: ordered, mutable
numbers_list = [1, 2, 3, 4, 5]
numbers_list.append(6)
print(numbers_list, type(numbers_list))

# tuple: ordered, immutable
numbers_tuple = (1, 2, 3, 4, 5)
# numbers_tuple.append(6)  # AttributeError: tuples can't change
print(numbers_tuple, type(numbers_tuple))

# set: unordered, unique items
numbers_set = {1, 2, 3, 4, 5, 5}  # duplicate 5 is dropped
numbers_set.add(6)
print(numbers_set, type(numbers_set))

# dict: key-value pairs
person_dict = {"name": "Alice", "age": 25, "height": 5.6}
person_dict["is_student"] = True
print(person_dict, type(person_dict))

