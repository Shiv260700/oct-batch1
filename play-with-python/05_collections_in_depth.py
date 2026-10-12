# Collections in depth: list, tuple, set, dict, and the collections module

from collections import Counter, defaultdict, namedtuple

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


# -----------------------------------------------------
# 6. Choosing the right data structure
# -----------------------------------------------------

# Need...                                  Use
# ordered items you'll add/remove/change   list
# fixed record that shouldn't change       tuple (or namedtuple / dataclass)
# unique items, fast "is x in here?"       set
# look up a value by a key                 dict

emails = ["a@x.com", "b@x.com", "a@x.com"]
print(len(set(emails)))         # 2 unique: set removes duplicates

blocked = {"spam@x.com", "bot@x.com"}  # set: `in` is fast even with millions
print("bot@x.com" in blocked)

prices = {"apple": 1.0, "bread": 2.5}  # dict: find a price by name
print(prices["bread"])


# -----------------------------------------------------
# 7. The collections module
# -----------------------------------------------------

# Counter: count things
word_counts = Counter("a b a c b a".split())
print(word_counts)                 # Counter({'a': 3, 'b': 2, 'c': 1})
print(word_counts.most_common(1))  # [('a', 3)]

# defaultdict: missing keys get a default value automatically
by_letter = defaultdict(list)
for name in ["Alice", "Bob", "Anna", "Ben"]:
    by_letter[name[0]].append(name)  # no need to check if the key exists
print(dict(by_letter))  # {'A': ['Alice', 'Anna'], 'B': ['Bob', 'Ben']}

# namedtuple: a tuple with named fields
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
print(p.x, p.y, p)  # 3 4 Point(x=3, y=4)
