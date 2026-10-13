# Comprehensions: build collections in one readable line

numbers = [1, 2, 3, 4, 5, 6]

# -----------------------------------------------------
# 1. List comprehension
# -----------------------------------------------------

# Loop version
squares = []
for n in numbers:
    squares.append(n * n)
print(squares)

# Comprehension version: [expression for item in iterable]
squares = [n * n for n in numbers]
print(squares)


# -----------------------------------------------------
# 2. With a condition (filter)
# -----------------------------------------------------

evens = [n for n in numbers if n % 2 == 0]
print(evens)

# if/else goes before the `for` (it transforms, not filters)
labels = ["even" if n % 2 == 0 else "odd" for n in numbers]
print(labels)


# -----------------------------------------------------
# 3. Dict and set comprehensions
# -----------------------------------------------------

names = ["alice", "bob", "charlie"]

name_lengths = {name: len(name) for name in names}
print(name_lengths)

first_letters = {name[0] for name in names}
print(first_letters)

prices = {"apple": 1.0, "banana": 0.5}
discounted = {item: price * 0.9 for item, price in prices.items()}
print(discounted)


# -----------------------------------------------------
# 4. Nested loops
# -----------------------------------------------------

pairs = [(x, y) for x in range(1, 3) for y in "ab"]
print(pairs)  # [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]

matrix = [[1, 2], [3, 4], [5, 6]]
flat = [n for row in matrix for n in row]
print(flat)


# -----------------------------------------------------
# 5. Generator expression: like a list comprehension, but lazy
# -----------------------------------------------------

total = sum(n * n for n in numbers)  # no list is built in memory
print(total)

# Tip: if a comprehension gets hard to read, use a normal loop.
