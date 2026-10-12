# Control flow: if, for, while

# -----------------------------------------------------
# 1. if / elif / else
# -----------------------------------------------------

score = 72

if score >= 90:
    grade = "A"
elif score >= 70:
    grade = "B"
else:
    grade = "C"
print(f"Grade: {grade}")

# One-line form (conditional expression)
status = "pass" if score >= 40 else "fail"
print(status)

# Empty values count as False
items = []
if not items:
    print("No items")


# -----------------------------------------------------
# 2. for loops
# -----------------------------------------------------

for fruit in ["apple", "banana", "cherry"]:
    print(fruit)

for i in range(3):          # 0, 1, 2
    print(i)

for i in range(2, 10, 3):   # start, stop, step: 2, 5, 8
    print(i)

for letter in "abc":        # strings are iterable too
    print(letter)


# -----------------------------------------------------
# 3. while loops
# -----------------------------------------------------

countdown = 3
while countdown > 0:
    print(countdown)
    countdown -= 1
print("Go!")


# -----------------------------------------------------
# 4. break and continue
# -----------------------------------------------------

for n in range(10):
    if n == 5:
        break       # stop the loop
    if n % 2 == 0:
        continue    # skip to the next item
    print(n)        # 1, 3


# -----------------------------------------------------
# 5. Loop helpers: enumerate and zip
# -----------------------------------------------------

names = ["Alice", "Bob", "Charlie"]
ages = [30, 25, 35]

for index, name in enumerate(names, start=1):
    print(index, name)

for name, age in zip(names, ages):  # walk two lists together
    print(f"{name} is {age}")


# -----------------------------------------------------
# 6. for ... else: runs only if the loop didn't break
# -----------------------------------------------------

for n in [3, 7, 11]:
    if n % 2 == 0:
        print("Found an even number")
        break
else:
    print("No even numbers")
