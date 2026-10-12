

# complex data type(s) aka data structures in python

# 1. list -> ordered collection of items
# 2. tuple -> ordered collection of items (immutable)
# 3. set -> unordered collection of unique items
# 4. dict -> collection of key-value pairs


# list
my_list = [1, 2, 3, 4, 5] # list of integers
print(my_list)
print(type(my_list))
my_list.append(6) # adding an item to the list
print(my_list)

# tuple
my_tuple = (1, 2, 3, 4, 5) # tuple of integers
print(my_tuple)
print(type(my_tuple))
# my_tuple.append(6) # this will raise an error because tuples are immutable
print(my_tuple)

# set
my_set = {1, 2, 3, 4, 5, 5} # set of integers
print(my_set)
print(type(my_set))
my_set.add(6) # adding an item to the set
print(my_set)


# dict
my_dict = {"name": "Alice", "age": 25, "height": 5.6} # dictionary with key-value pairs
print(my_dict)
print(type(my_dict))
my_dict["is_student"] = True # adding a new key-value pair to the dictionary
print(my_dict)
