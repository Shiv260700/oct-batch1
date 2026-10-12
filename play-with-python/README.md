# Play with Python

Small, runnable Python examples, one topic per file, meant to be read in order.

## Run an example

From the repo root:

```sh
python3 play-with-python/01_hello_world.py
```

Each file runs on its own and prints its results, so read the code and compare it with the output.

## Lessons

| # | File | Topic |
|---|------|-------|
| 01 | [01_hello_world.py](01_hello_world.py) | Printing to the console |
| 02 | [02_data_types.py](02_data_types.py) | `str`, `int`, `float`, `bool`, `None`, and `list`, `tuple`, `set`, `dict` |
| 03 | [03_operators_and_strings.py](03_operators_and_strings.py) | Operators, f-strings, slicing, string methods, converting between types |
| 04 | [04_control_flow.py](04_control_flow.py) | `if`/`elif`/`else`, `for`, `while`, `break`/`continue`, `enumerate`, `zip` |
| 05 | [05_collections_in_depth.py](05_collections_in_depth.py) | List, tuple, set and dict methods; nested data |
| 06 | [06_comprehensions.py](06_comprehensions.py) | List, dict and set comprehensions; generator expressions |
| 07 | [07_functions.py](07_functions.py) | Arguments, return values, scope, first-class functions, closures |
| 08 | [08_lambda_map_filter.py](08_lambda_map_filter.py) | `lambda`, `map`, `filter`, `sorted(key=)` |
| 09 | [09_higher_order_functions.py](09_higher_order_functions.py) | Functions that take and return functions |
| 10 | [10_decorators.py](10_decorators.py) | The `@` syntax; decorators with arguments |
| 11 | [11_classes.py](11_classes.py) | Classes, inheritance, dunder methods, `@property`, `@dataclass` |
| 12 | [12_exceptions.py](12_exceptions.py) | `try`/`except`/`else`/`finally`, `raise`, custom exceptions |
| 13 | [13_context_manager.py](13_context_manager.py) | `__enter__`/`__exit__` and the `with` statement |
| 14 | [14_iterators_generators.py](14_iterators_generators.py) | `iter`/`next`, `yield`, `@contextmanager` |
| 15 | [15_modules_and_imports.py](15_modules_and_imports.py) | `import`, your own modules, `__name__ == "__main__"` |
| 16 | [16_file_handling.py](16_file_handling.py) | Reading and writing text, CSV and JSON |

## Supporting files

- `lunch_menu.txt` is read by lessons 13 and 16.
- `greetings.py` is the module imported in lesson 15. Files whose names start with a digit can't be imported, so shared code lives here.
- `output/` is created by lesson 16 for the files it writes. Git ignores it.
