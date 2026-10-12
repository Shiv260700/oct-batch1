# Operators and strings

# -----------------------------------------------------
# 1. Arithmetic operators
# -----------------------------------------------------

a, b = 17, 5

print(a + b)   # 22  addition
print(a - b)   # 12  subtraction
print(a * b)   # 85  multiplication
print(a / b)   # 3.4 division (always a float)
print(a // b)  # 3   floor division (drops the decimal)
print(a % b)   # 2   remainder
print(a ** 2)  # 289 power

count = 10
count += 5  # same as: count = count + 5
print(count)


# -----------------------------------------------------
# 2. Comparison and logical operators
# -----------------------------------------------------

print(a > b, a == b, a != b)  # True False True

age = 20
has_ticket = True
print(age >= 18 and has_ticket)  # both must be True
print(age < 12 or age > 60)      # at least one must be True
print(not has_ticket)            # flips True/False

print(10 < age < 30)  # chained comparison


# -----------------------------------------------------
# 3. Strings: creating and combining
# -----------------------------------------------------

first = "Ada"
last = 'Lovelace'  # single or double quotes both work

full = first + " " + last
print(full)
print("-" * 20)  # repeat a string

# f-strings put values inside {}
print(f"{first} was born in {1815}.")
print(f"{3.14159:.2f}")  # format to 2 decimal places

poem = """Multi-line
strings use
triple quotes."""
print(poem)


# -----------------------------------------------------
# 4. Indexing and slicing
# -----------------------------------------------------

word = "Python"
#       P  y  t  h  o  n
#       0  1  2  3  4  5
#      -6 -5 -4 -3 -2 -1

print(word[0])    # P
print(word[-1])   # n
print(word[0:3])  # Pyt  (end is not included)
print(word[2:])   # thon
print(word[::-1])  # nohtyP  (reversed)
print(len(word))  # 6


# -----------------------------------------------------
# 5. Common string methods (strings never change, methods return new ones)
# -----------------------------------------------------

text = "  Hello, World  "

print(text.strip())                     # remove outer spaces
print(text.lower(), text.upper())
print(text.replace("World", "Python"))
print("a,b,c".split(","))               # ['a', 'b', 'c']
print("-".join(["a", "b", "c"]))        # a-b-c
print("World" in text)                  # True
print("report.pdf".endswith(".pdf"))    # True
print("42".isdigit())                   # True


# -----------------------------------------------------
# 6. Converting between types
# -----------------------------------------------------

print(int("10") + 5)    # 15
print(str(10) + "5")    # 105
print(float("3.5"))     # 3.5
print(bool(0), bool(""), bool("hi"))  # False False True
