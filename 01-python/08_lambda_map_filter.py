# lambda, map, filter, sorted: built-in higher-order functions

# -----------------------------------------------------
# 1. lambda: a small, unnamed, one-expression function
# -----------------------------------------------------

def square(n):
    return n * n


square_lambda = lambda n: n * n  # same as square() above

print(square(4))
print(square_lambda(4))
print((lambda a, b: a + b)(2, 3))  # define and call at once


# -----------------------------------------------------
# 2. map: apply a function to every item
# -----------------------------------------------------

numbers = [1, 2, 3, 4, 5]

squares = map(lambda n: n * n, numbers)  # returns a lazy map object
print(list(squares))                     # list() runs it

names = ["alice", "bob", "charlie"]
print(list(map(str.upper, names)))  # any function works, not just lambda


# -----------------------------------------------------
# 3. filter: keep items where the function returns True
# -----------------------------------------------------

evens = filter(lambda n: n % 2 == 0, numbers)
print(list(evens))

words = ["apple", "", "banana", "", "cherry"]
print(list(filter(None, words)))  # None keeps only truthy items


# -----------------------------------------------------
# 4. sorted(key=): sort by a value computed from each item
# -----------------------------------------------------

fruits = ["banana", "kiwi", "apple", "cherry"]
print(sorted(fruits))                         # alphabetical
print(sorted(fruits, key=len))                # by length
print(sorted(fruits, key=len, reverse=True))  # longest first

people = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35},
]
by_age = sorted(people, key=lambda p: p["age"])
print([p["name"] for p in by_age])

# min and max take key= too
print(max(people, key=lambda p: p["age"])["name"])  # oldest


# -----------------------------------------------------
# 5. Putting it together: map + filter + sorted
# -----------------------------------------------------

prices = [120, 45, 300, 80, 15]

# 10% off items over 50, cheapest first
discounted = sorted(map(lambda p: p * 0.9, filter(lambda p: p > 50, prices)))
print(discounted)

# Tip: comprehensions often read better than map/filter
print(sorted(p * 0.9 for p in prices if p > 50))
