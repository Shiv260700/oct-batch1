# itertools: building blocks for working with iterators
#
# Most itertools functions are lazy: they produce items on demand.

from itertools import (
    accumulate, chain, combinations, count, cycle, groupby,
    islice, permutations, product, takewhile, zip_longest,
)

# -----------------------------------------------------
# 1. Infinite iterators (always limit them!)
# -----------------------------------------------------

print(list(islice(count(10, 5), 4)))        # [10, 15, 20, 25]
print(list(islice(cycle("AB"), 5)))         # ['A', 'B', 'A', 'B', 'A']

ids = count(1)                              # simple ID generator
print(next(ids), next(ids), next(ids))      # 1 2 3


# -----------------------------------------------------
# 2. Slicing and combining
# -----------------------------------------------------

print(list(islice(range(100), 2, 10, 3)))   # like [2:10:3] on any iterator
print(list(chain([1, 2], (3, 4), "ab")))    # join iterables end to end
print(list(zip_longest("abc", [1, 2], fillvalue="-")))  # zip without dropping


# -----------------------------------------------------
# 3. Running totals and stopping early
# -----------------------------------------------------

daily_sales = [100, 250, 75, 300]
print(list(accumulate(daily_sales)))         # [100, 350, 425, 725]
print(list(accumulate(daily_sales, max)))    # running maximum

readings = [3, 5, 8, 12, 4, 2]
print(list(takewhile(lambda r: r < 10, readings)))  # [3, 5, 8]: stops at 12


# -----------------------------------------------------
# 4. groupby: group consecutive items (sort first!)
# -----------------------------------------------------

orders = [
    ("fruit", "apple"), ("dairy", "milk"),
    ("fruit", "banana"), ("dairy", "cheese"),
]
orders.sort(key=lambda o: o[0])  # groupby only groups neighbors
for category, items in groupby(orders, key=lambda o: o[0]):
    print(category, [item for _, item in items])


# -----------------------------------------------------
# 5. Combinatorics
# -----------------------------------------------------

print(list(product("AB", [1, 2])))      # every pairing: A1 A2 B1 B2
print(list(combinations("ABC", 2)))     # pairs, order doesn't matter
print(list(permutations("ABC", 2)))     # pairs, order matters

# Grid search: try every combination of settings
for lr, batch in product([0.1, 0.01], [16, 32]):
    print(f"lr={lr}, batch={batch}")


# -----------------------------------------------------
# 6. Batching a stream (common when processing big data)
# -----------------------------------------------------

def batched(iterable, size):
    """Yield lists of up to `size` items. (Built in as itertools.batched in 3.12+.)"""
    it = iter(iterable)
    while batch := list(islice(it, size)):
        yield batch


for batch in batched(range(10), 4):
    print(batch)  # [0, 1, 2, 3] / [4, 5, 6, 7] / [8, 9]
