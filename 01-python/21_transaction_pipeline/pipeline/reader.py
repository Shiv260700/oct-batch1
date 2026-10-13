# Step 1: read

import csv
from pathlib import Path
from typing import Iterator, Union


def read_rows(path: Union[str, Path]) -> Iterator[dict[str, str]]:
    """Yield one CSV row at a time, so huge files never load fully into memory."""
    with open(path, newline="") as f:
        yield from csv.DictReader(f)
