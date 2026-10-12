# Play with Python

Small, runnable Python examples, one topic per file, meant to be read in order.

## Run an example

From the repo root:

```sh
python3 play-with-python/01_hello_world.py
```

Each file runs on its own and prints its results, so read the code and compare it with the output.

Lessons 20 and 21 need pytest (`python3 -m pip install pytest`). To run every test:

```sh
python3 -m pytest play-with-python -v
```

## Lessons

| # | File | Topic |
|---|------|-------|
| 01 | [01_hello_world.py](01_hello_world.py) | Printing to the console |
| 02 | [02_data_types.py](02_data_types.py) | `str`, `int`, `float`, `bool`, `None`, and `list`, `tuple`, `set`, `dict` |
| 03 | [03_operators_and_strings.py](03_operators_and_strings.py) | Operators, f-strings, slicing, string methods, converting between types |
| 04 | [04_control_flow.py](04_control_flow.py) | `if`/`elif`/`else`, `for`, `while`, `break`/`continue`, `enumerate`, `zip` |
| 05 | [05_collections_in_depth.py](05_collections_in_depth.py) | List, tuple, set and dict methods; choosing a structure; `Counter`, `defaultdict`, `namedtuple` |
| 06 | [06_comprehensions.py](06_comprehensions.py) | List, dict and set comprehensions; generator expressions |
| 07 | [07_functions.py](07_functions.py) | Arguments, `*args`/`**kwargs`, return values, scope, first-class functions, closures |
| 08 | [08_lambda_map_filter.py](08_lambda_map_filter.py) | `lambda`, `map`, `filter`, `sorted(key=)` |
| 09 | [09_higher_order_functions.py](09_higher_order_functions.py) | Functions that take and return functions |
| 10 | [10_decorators.py](10_decorators.py) | The `@` syntax; decorators with arguments; a `@timer` with `functools.wraps` |
| 11 | [11_classes.py](11_classes.py) | Classes, inheritance, dunder methods, `@property`, `@dataclass`, `__call__` and the PyTorch `forward()` pattern |
| 12 | [12_exceptions.py](12_exceptions.py) | `try`/`except`/`else`/`finally`, `raise`, custom exceptions |
| 13 | [13_context_manager.py](13_context_manager.py) | `__enter__`/`__exit__` and the `with` statement |
| 14 | [14_iterators_generators.py](14_iterators_generators.py) | `iter`/`next`, `yield`, `@contextmanager`, streaming a large file |
| 15 | [15_modules_and_imports.py](15_modules_and_imports.py) | `import`, your own modules, `__name__ == "__main__"` |
| 16 | [16_file_handling.py](16_file_handling.py) | Reading and writing text, CSV and JSON |
| 17 | [17_type_hints.py](17_type_hints.py) | Type hints for variables, functions, collections, `Optional`, `Callable` |
| 18 | [18_itertools.py](18_itertools.py) | `islice`, `chain`, `accumulate`, `groupby`, `product`, batching |
| 19 | [19_packages/](19_packages/main.py) | A package with `__init__.py`, relative imports, a subpackage. Run `19_packages/main.py`. |
| 20 | [20_testing_with_pytest/](20_testing_with_pytest/test_calculator.py) | `assert`, `pytest.raises`, `parametrize`, fixtures, `tmp_path` |

## Guided practice: transaction pipeline

[21_transaction_pipeline/](21_transaction_pipeline/main.py) brings the lessons together. It reads `transactions.csv` and passes it through:

```
read_rows -> valid_transactions -> filters -> summarize
```

Every step is a generator, so only one row is in memory at a time. Invalid rows are skipped and reported. The `pipeline/` package has one module per step, and `tests/` covers each one.

```sh
python3 play-with-python/21_transaction_pipeline/main.py
python3 -m pytest play-with-python/21_transaction_pipeline -v
```

## Checkpoint

1. **Tested function.** Add a `by_date_range(transactions, start, end)` filter to `pipeline/filters.py`, with pytest tests covering a normal range, an empty result, and the boundary dates.
2. **Generator explanation.** In a few sentences, explain why `summarize(valid_transactions(read_rows(path)))` can handle a 10 GB file without running out of memory, and what would change if `read_rows` returned a list.

## Supporting files

- `lunch_menu.txt` is read by lessons 13 and 16.
- `greetings.py` is the module imported in lesson 15. Files whose names start with a digit can't be imported, so shared code lives here.
- `output/` is created by lessons 14 and 16 for the files they write. Git ignores it.
