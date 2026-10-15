"""Create the lab datasets (same files every time).

data/students.csv (lab 1): 1,000 students, the final-exam marks we want to predict.

The data is synthetic, so we know the truth, but it has the problems real data has:
missing values, a few students who were ill on exam day, a category column, and one
column that leaks the answer. Re-running gives exactly the same file (seed 7).
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 1000
stream = rng.choice(["science", "commerce", "arts"], size=n, p=[0.4, 0.35, 0.25])
hours = rng.gamma(4, 2.2, n).clip(0, 30).round(1)                 # study hours per week
attendance = rng.normal(85, 8, n).clip(45, 100).round(0)          # % of classes attended
sleep = rng.normal(7.2, 1.1, n).clip(4, 10).round(1)              # hours per night
prev = rng.normal(62, 12, n).clip(20, 98).round(0)                # last term's marks
tuition = rng.random(n) < 0.3

bonus = pd.Series(stream).map({"science": 4, "commerce": 2, "arts": 0}).to_numpy()
marks = (8 + 1.6 * hours + 0.25 * attendance - 2.0 * (sleep - 7.5) ** 2   # sleep: a hump, best near 7.5 h
         + 0.45 * prev + bonus + 3 * tuition + rng.normal(0, 4, n))
ill = rng.random(n) < 0.02                                         # ill on exam day: outliers
marks = np.where(ill, marks - rng.uniform(25, 40, n), marks).clip(0, 100).round(0)

df = pd.DataFrame({
    "student_id": [f"S{i:04d}" for i in range(n)],
    "stream": stream, "study_hours": hours, "attendance": attendance, "sleep_hours": sleep,
    "prev_marks": prev, "tuition": np.where(tuition, "yes", "no"),
    "grade": pd.cut(marks, [-1, 39, 54, 69, 84, 100], labels=["F", "D", "C", "B", "A"]),  # made AFTER the exam: a leak
    "final_marks": marks,
})
df.loc[rng.random(n) < 0.04, "attendance"] = np.nan                # 4% not recorded
df.loc[rng.random(n) < 0.03, "sleep_hours"] = np.nan               # 3% didn't answer
Path("data").mkdir(exist_ok=True)
df.to_csv("data/students.csv", index=False)
print(df.shape, "ill:", int(ill.sum()), "→ data/students.csv")

# ---------------------------------------------------------------- data/dropout.csv (lab 2)
# 3,000 students. Everything is known at week 6 of the term, except `dropped_out` (the target,
# known at term end) and `exit_survey_done` (only filled in when a student leaves: a leak).
rng = np.random.default_rng(11)
n = 3000
attendance = rng.beta(8, 2, n).round(2) * 100                       # % of classes in weeks 1–6
submitted = rng.beta(6, 2, n).round(2) * 100                        # % of assignments handed in
quiz = rng.normal(62, 15, n).clip(0, 100).round(0)                  # average quiz score
logins = rng.poisson(5, n)                                          # learning-portal logins per week
distance = rng.gamma(2, 6, n).round(1)                              # km from home to college
job = rng.random(n) < 0.25                                          # part-time job
scholarship = rng.random(n) < 0.2
stream2 = rng.choice(["science", "commerce", "arts"], size=n, p=[0.4, 0.35, 0.25])

score = (-4.1 - 0.09 * (attendance - 80) - 0.05 * (submitted - 75) - 0.045 * (quiz - 62)
         - 0.35 * (logins - 5) + 0.045 * distance + 1.3 * job - 1.2 * scholarship
         + 1.3 * job * (attendance < 70))                           # a job hurts most when attendance is already low
dropped = rng.random(n) < 1 / (1 + np.exp(-score))
d2 = pd.DataFrame({
    "student_id": [f"D{i:04d}" for i in range(n)], "stream": stream2,
    "attendance_wk6": attendance.round(0), "assignments_submitted": submitted.round(0), "quiz_avg": quiz,
    "logins_per_week": logins, "distance_km": distance,
    "part_time_job": np.where(job, "yes", "no"), "scholarship": np.where(scholarship, "yes", "no"),
    "exit_survey_done": np.where(dropped & (rng.random(n) < 0.9), "yes", "no"),   # filled in AFTER leaving: a leak
    "dropped_out": dropped.astype(int),
})
d2.loc[rng.random(n) < 0.05, "quiz_avg"] = np.nan                   # missed every quiz so far
d2.to_csv("data/dropout.csv", index=False)
print(d2.shape, f"dropout rate {d2.dropped_out.mean():.1%} → data/dropout.csv")
