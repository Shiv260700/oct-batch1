# Collections in depth: list, tuple, set, dict

# -----------------------------------------------------
# 1. list
# -----------------------------------------------------

nums = [5, 3, 8, 1]

print(nums[0], nums[-1])  # first, last
print(nums[1:3])          # slice: [3, 8]

nums.append(9)       # add to end
nums.insert(0, 7)    # add at index 0
nums.remove(8)       # remove first matching value
last = nums.pop()    # remove and return the last item
print(nums, last)

nums.sort()          # sorts in place
print(nums)
print(len(nums), sum(nums), min(nums), max(nums))
print(3 in nums)     # membership test

nums[0] = 100        # lists are mutable
print(nums)


# -----------------------------------------------------
# 2. tuple
# -----------------------------------------------------

point = (3, 4)
x, y = point          # unpacking
print(x, y)

a, b = 1, 2
a, b = b, a           # swap using tuples
print(a, b)

single = (42,)        # one-item tuple needs a trailing comma
print(type(single))


# -----------------------------------------------------
# 3. set
# -----------------------------------------------------

python_devs = {"Alice", "Bob", "Charlie"}
java_devs = {"Bob", "Dave"}

print(python_devs | java_devs)  # union: in either
print(python_devs & java_devs)  # intersection: in both
print(python_devs - java_devs)  # difference: only in python_devs

unique = set([1, 2, 2, 3, 3, 3])  # quick way to remove duplicates
print(unique)


# -----------------------------------------------------
# 4. dict
# -----------------------------------------------------

person = {"name": "Alice", "age": 30}

print(person["name"])
print(person.get("email"))             # None instead of KeyError
print(person.get("email", "n/a"))      # with a default

person["email"] = "alice@example.com"  # add or update
del person["age"]                      # remove a key
print(person)

for key, value in person.items():      # loop over key-value pairs
    print(key, "->", value)

print(list(person.keys()))
print(list(person.values()))
print("name" in person)                # checks keys

# Count words with a dict
counts = {}
for word in "a b a c b a".split():
    counts[word] = counts.get(word, 0) + 1
print(counts)  # {'a': 3, 'b': 2, 'c': 1}


# -----------------------------------------------------
# 5. Nesting
# -----------------------------------------------------

team = {
    "name": "Core",
    "members": ["Alice", "Bob"],
    "lead": {"name": "Alice", "years": 5},
}
print(team["members"][1])     # Bob
print(team["lead"]["years"])  # 5
