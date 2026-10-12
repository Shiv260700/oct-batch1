# Exceptions: handling errors instead of crashing

# -----------------------------------------------------
# 1. try / except
# -----------------------------------------------------

try:
    result = 10 / 0
except ZeroDivisionError:
    print("Can't divide by zero")


# -----------------------------------------------------
# 2. Catching different errors
# -----------------------------------------------------

def to_number(value):
    try:
        return int(value)
    except ValueError:
        print(f"{value!r} is not a number")
    except TypeError as e:  # `as e` gives you the error object
        print(f"Wrong type: {e}")


to_number("42")
to_number("abc")
to_number(None)


# -----------------------------------------------------
# 3. else and finally
# -----------------------------------------------------

try:
    value = int("7")
except ValueError:
    print("Bad input")
else:
    print("No error, value is", value)  # only if try succeeded
finally:
    print("finally always runs")       # cleanup goes here


# -----------------------------------------------------
# 4. Raising your own errors
# -----------------------------------------------------

def withdraw(balance, amount):
    if amount > balance:
        raise ValueError(f"Insufficient funds: balance {balance}, asked {amount}")
    return balance - amount


try:
    withdraw(100, 500)
except ValueError as e:
    print(e)


# -----------------------------------------------------
# 5. Custom exception classes
# -----------------------------------------------------

class InvalidAgeError(Exception):
    pass


def set_age(age):
    if age < 0:
        raise InvalidAgeError(f"Age can't be negative: {age}")
    return age


try:
    set_age(-5)
except InvalidAgeError as e:
    print(type(e).__name__, "-", e)


# Tip: catch specific errors. A bare `except:` hides real bugs.
