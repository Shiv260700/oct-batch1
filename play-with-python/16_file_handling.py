# File handling: reading and writing text, CSV and JSON

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT = HERE / "output"   # generated files go here (git-ignored)
OUTPUT.mkdir(exist_ok=True)

# -----------------------------------------------------
# 1. Reading a text file
# -----------------------------------------------------

menu_path = HERE / "lunch_menu.txt"

with open(menu_path) as f:   # "r" (read) is the default mode
    print(f.read())          # whole file as one string

with open(menu_path) as f:
    for line in f:           # one line at a time (good for big files)
        print(line.strip())


# -----------------------------------------------------
# 2. Writing and appending
# -----------------------------------------------------

notes_path = OUTPUT / "notes.txt"

with open(notes_path, "w") as f:  # "w" creates or overwrites
    f.write("First line\n")

with open(notes_path, "a") as f:  # "a" adds to the end
    f.write("Second line\n")

print(notes_path.read_text())     # pathlib shortcut for small files


# -----------------------------------------------------
# 3. CSV
# -----------------------------------------------------

students = [
    {"name": "Alice", "score": 90},
    {"name": "Bob", "score": 75},
]
csv_path = OUTPUT / "students.csv"

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "score"])
    writer.writeheader()
    writer.writerows(students)

with open(csv_path, newline="") as f:
    for row in csv.DictReader(f):  # each row is a dict of strings
        print(row["name"], int(row["score"]))


# -----------------------------------------------------
# 4. JSON
# -----------------------------------------------------

json_path = OUTPUT / "students.json"

with open(json_path, "w") as f:
    json.dump(students, f, indent=2)  # Python -> JSON file

with open(json_path) as f:
    loaded = json.load(f)             # JSON file -> Python
print(loaded[0]["name"])

text = json.dumps({"ok": True})       # to/from a string: dumps / loads
print(text, json.loads(text))


# -----------------------------------------------------
# 5. Handling a missing file
# -----------------------------------------------------

try:
    with open(HERE / "missing.txt") as f:
        f.read()
except FileNotFoundError:
    print("File not found")
