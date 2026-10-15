"""Build the labs2 notebooks (solution + starter) from this one file.

    python build.py            write notebooks
    python build.py --run      write, then execute every solution notebook (must pass)
"""
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent


def md(text):
    return ("md", text.strip("\n"), None)


def code(text, stub=None):
    """A code cell; `stub` replaces it in the starter notebook."""
    return ("code", text.strip("\n"), None if stub is None else stub.strip("\n"))


def build(name, cells):
    for variant in ("solution", "starter"):
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        for kind, text, stub in cells:
            if kind == "md":
                nb.cells.append(nbf.v4.new_markdown_cell(text))
            else:
                cell = nbf.v4.new_code_cell(stub if (variant == "starter" and stub is not None) else text)
                if stub is not None:
                    cell.metadata["tags"] = ["solution"] if variant == "solution" else ["todo"]
                nb.cells.append(cell)
        out = HERE / (f"{name}.ipynb" if variant == "solution" else f"starter/{name}.ipynb")
        out.parent.mkdir(exist_ok=True)
        nbf.write(nb, out)
    return HERE / f"{name}.ipynb"


NOTEBOOKS = {}

# ---------------------------------------------------------------- Lab 1 · prediction
NOTEBOOKS["01-prediction"] = [
    md("""
# Lab 1 · Prediction: final-exam marks
**Goal:** predict each student's final marks from what is known *before* the exam, and prove how good the prediction is.

**You will practise**
- Look at the data before modelling
- Lock a test set away first
- Start from a baseline
- Find and remove a leak
- Build a pipeline: impute, scale, one-hot
- Compare models with cross-validation
- Test once, report a range
- Read the mistakes, explain the model
- Save the model, check inputs before trusting it

**How to work:** 🧠 = write your guess first · ✓ = the notebook proves the result
"""),
    md("""
## 0 · Setup
- One seed for everything
- Print library versions, so results can be reproduced
"""),
    code("""import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import HuberRegressor, LinearRegression
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler

SEED = 0
warnings.filterwarnings("ignore", category=FutureWarning)
plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.grid": True, "font.size": 12})
print("pandas", pd.__version__, "· scikit-learn", sklearn.__version__)"""),

    md("""
## 1 · Load the data
- 1,000 students
- Target: `final_marks`
- Missing file? Run `python make_data.py`
"""),
    code("""df = pd.read_csv("data/students.csv")
print(df.shape)
df.head()"""),
    code("""df.info()"""),
    md("""
### Check three things first
- Missing values
- Ranges (min, max)
- Categories and their counts
"""),
    code("""print("missing per column:\\n", df.isna().sum()[df.isna().sum() > 0], "\\n")
print(df.describe().round(1).T[["mean", "min", "max"]], "\\n")
print(df["stream"].value_counts().to_dict(), df["tuition"].value_counts().to_dict())"""),
    md("""
### Each clue against the target
- Is it a line, a curve, or nothing?
"""),
    code("""fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
for ax, col in zip(axes, ["study_hours", "attendance", "sleep_hours", "prev_marks"]):
    ax.scatter(df[col], df["final_marks"], s=6, alpha=0.4)
    ax.set_xlabel(col)
axes[0].set_ylabel("final_marks")
plt.tight_layout(); plt.show()"""),
    md("""
**What to notice**
- Study hours, previous marks: roughly straight lines up
- Sleep: a **hump**, best near 7.5 hours; a straight line can't fit it
- A few dots far **below** the cloud: students ill on exam day
"""),

    md("""
## 2 · 🧠 Predict first
- Asha: science, 12 study hours/week, 92% attendance, sleeps 7.5 h, 70 last term, no tuition
- Write your guess before the model does
"""),
    code("""my_guess_for_asha = 80""", stub="""my_guess_for_asha = None   # your number"""),

    md("""
## 3 · Lock away a test set
- Put 20% aside **before** any modelling
- Use it **once**, at the very end
- Compare and tune on the other 80% only
"""),
    code("""target = "final_marks"
X = df.drop(columns=[target, "student_id"])     # an ID is never a clue
y = df[target]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)
print(f"train {len(X_train)} · test {len(X_test)} (locked)")"""),

    md("""
## 4 · Baseline
- Always predict the training average; every real model must beat it
- Score: **MAE** (mean absolute error) = average miss, in marks
- **5-fold cross-validation:** train on 4 parts, score the 5th, rotate, average
"""),
    code("""cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

def cv_mae(model, X_=None):
    \"\"\"Average MAE over 5 folds of the training set.\"\"\"
    X_ = X_train if X_ is None else X_
    return -cross_val_score(model, X_, y_train, cv=cv, scoring="neg_mean_absolute_error").mean()

baseline = cv_mae(DummyRegressor(strategy="mean"))
print(f"baseline (always the average): MAE {baseline:.2f} marks")"""),

    md("""
## 5 · 🧠 A suspicious column: `grade`
- How good would a model using **only** `grade` look?
"""),
    code("""grade_only = Pipeline([
    ("prep", ColumnTransformer([("g", OneHotEncoder(), ["grade"])])),
    ("model", LinearRegression()),
])
print(f"grade only: MAE {cv_mae(grade_only):.2f}  vs baseline {baseline:.2f}")"""),
    md("""
**Too good to be true**
- Ask: *does this column exist at prediction time?*
- `grade` is computed from the final marks, after the exam
- It is a **leak**: drop it
"""),
    code("""X_train = X_train.drop(columns="grade")
X_test = X_test.drop(columns="grade")
assert "grade" not in X_train.columns
print("✓ leak removed; columns:", list(X_train.columns))"""),

    md("""
## 6 · Pipeline: preparation inside the model
- Numbers: fill missing with the median, then standardise
- Categories: one-hot `stream`; `tuition` → 0/1
- Inside a `Pipeline`, these steps learn from training folds only (no hidden leak) and run automatically at prediction time
"""),
    code("""numeric = ["study_hours", "attendance", "sleep_hours", "prev_marks"]
categorical = ["stream", "tuition"]

def make_prep(sleep_curve=False):
    parts = [
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric),
        ("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), categorical),
    ]
    if sleep_curve:   # a curved clue: sleep and sleep²
        parts.append(("sleep²", make_pipeline(SimpleImputer(strategy="median"), PolynomialFeatures(2, include_bias=False), StandardScaler()), ["sleep_hours"]))
    return ColumnTransformer(parts)

make_prep().fit(X_train).get_feature_names_out()"""),

    md("""
## 7 · 🧠 Compare models fairly
- Same folds, same data, same score
- Rank them before running

| Model | Idea |
|---|---|
| linear | a straight line in every clue |
| linear + sleep² | adds a curved clue for the sleep hump |
| Huber + sleep² | same, but outliers pull less |
| random forest | many trees, averaged |
| boosting | trees that fix each other's mistakes |
"""),
    code("""my_ranking = ["huber + sleep²", "linear + sleep²", "linear", "boosting", "random forest"]""",
         stub="""my_ranking = None   # list the five names, best first"""),
    code("""candidates = {
    "linear": Pipeline([("prep", make_prep()), ("model", LinearRegression())]),
    "linear + sleep²": Pipeline([("prep", make_prep(True)), ("model", LinearRegression())]),
    "huber + sleep²": Pipeline([("prep", make_prep(True)), ("model", HuberRegressor(max_iter=1000))]),
    "random forest": Pipeline([("prep", make_prep()), ("model", RandomForestRegressor(300, random_state=SEED, n_jobs=-1))]),
    "boosting": Pipeline([("prep", make_prep()), ("model", HistGradientBoostingRegressor(random_state=SEED))]),
}
results = pd.Series({name: cv_mae(m) for name, m in candidates.items()}).sort_values()
results.loc["baseline"] = baseline
print(results.round(2).to_string())""",
         stub="""candidates = {
    "linear": Pipeline([("prep", make_prep()), ("model", LinearRegression())]),
    # TODO: add "linear + sleep²", "huber + sleep²", "random forest", "boosting"
}
# TODO: results = pd.Series({name: cv_mae(m) for ...}).sort_values()"""),
    code("""results.drop("baseline").plot.barh(color="#2F5FD0"); plt.axvline(baseline, c="grey", ls="--", label="baseline")
plt.xlabel("cross-validated MAE (lower is better)"); plt.legend(); plt.gca().invert_yaxis(); plt.show()
assert results.idxmin() == "huber + sleep²" and results["linear + sleep²"] < results["linear"] < baseline
print("✓ the curved clue and the outlier-proof loss win; fancy trees don't beat knowing the shape")"""),
    md("""
**Lesson**
- Knowing the shape of the problem (a hump, a few outliers) beat fancier models
- Try the simple, well-understood model first
"""),

    md("""
## 8 · Final test: once
- Train on all 800 training students
- Score the 200 locked students **one time**
- Report a **range** (bootstrap), not just one number
"""),
    code("""final_model = candidates["huber + sleep²"].fit(X_train, y_train)
pred = final_model.predict(X_test)
errors = np.abs(pred - y_test.to_numpy())

rng = np.random.default_rng(SEED)
boot = [errors[rng.integers(0, len(errors), len(errors))].mean() for _ in range(5000)]
low, high = np.percentile(boot, [2.5, 97.5])
test_baseline = np.abs(y_train.mean() - y_test).mean()
print(f"test MAE {errors.mean():.2f} marks (95% range {low:.2f}–{high:.2f}) · baseline {test_baseline:.2f}")"""),
    code("""assert high < test_baseline * 0.6
print(f"✓ proof: even the worst likely MAE ({high:.2f}) is far below the baseline ({test_baseline:.2f})")"""),

    md("""
## 9 · Read the mistakes
- Predicted vs real
- What do the worst misses have in common?
"""),
    code("""plt.scatter(y_test, pred, s=10, alpha=0.6); plt.plot([0, 100], [0, 100], c="grey", ls="--")
plt.xlabel("real marks"); plt.ylabel("predicted"); plt.title("Above the line = we over-predicted"); plt.show()

worst = X_test.assign(real=y_test, predicted=pred.round(1), miss=(y_test - pred).round(1)).sort_values("miss").head(5)
worst"""),
    md("""
**What the mistakes say**
- Worst misses: real marks far **below** the prediction: the ill-on-exam-day students
- No clue in the data predicts that: unavoidable, not a bug
- The data has ±4 marks of random noise, so MAE ≈ 3.2 is the best possible
"""),

    md("""
## 10 · Explain the model
- **Permutation importance:** shuffle one column, see how much the error grows
- Bigger growth = the model relies on that clue more
"""),
    code("""imp = permutation_importance(final_model, X_test, y_test, n_repeats=10, random_state=SEED, scoring="neg_mean_absolute_error")
importance = pd.Series(imp.importances_mean, index=X_test.columns).sort_values()
importance.plot.barh(color="#A9520E"); plt.xlabel("MAE increase when shuffled (marks)"); plt.show()
assert importance.idxmax() == "study_hours"
print("✓ study hours matter most, then previous marks, then sleep")"""),

    md("""
## 11 · Save and use the model
- Save the **whole pipeline** (preparation + model) in one file
- New data then needs no manual steps
"""),
    code("""Path("models").mkdir(exist_ok=True)
joblib.dump(final_model, "models/marks_model.joblib")

loaded = joblib.load("models/marks_model.joblib")
asha = pd.DataFrame([{"stream": "science", "study_hours": 12, "attendance": 92, "sleep_hours": 7.5,
                      "prev_marks": 70, "tuition": "no"}])
asha_pred = float(loaded.predict(asha)[0])
print(f"Asha: model {asha_pred:.1f} · your guess {my_guess_for_asha}")"""),
    code("""assert abs(asha_pred - 85.7) < 2     # the true rule (we made the data) gives 85.7
print("✓ the saved pipeline predicts Asha within 2 marks of the truth")"""),
    md("""
### 🧠 Messy input
- A missing value and a stream the model never saw
- Will it crash, or answer? Will the answer be good?
"""),
    code("""messy = asha.assign(attendance=np.nan, stream="vocational")
messy_pred = float(loaded.predict(messy)[0])
print(f"Asha with messy input: {messy_pred:.1f} (clean: {asha_pred:.1f})")"""),
    md("""
**Runs ≠ right**
- It answers, but ≈ 20 marks lower: the unknown stream got no bonus
- In a real service, check inputs first: flag unknown categories and missing values
"""),
    code("""def check_input(row):
    \"\"\"Return a list of problems that make a prediction untrustworthy.\"\"\"
    problems = [f"unknown {c}: {row[c]!r}" for c in categorical if row[c] not in set(X_train[c])]
    problems += [f"missing {c}" for c in numeric if pd.isna(row[c])]
    return problems

print("clean:", check_input(asha.iloc[0]) or "ok")
print("messy:", check_input(messy.iloc[0]))
assert check_input(asha.iloc[0]) == [] and len(check_input(messy.iloc[0])) == 2
print("✓ flag untrustworthy inputs before trusting the number")"""),

    md("""
## 12 · Your turn
- Remove sleep² from the Huber model: how much worse is CV MAE?
- Swap Huber for plain linear: compare the worst 5 misses
- Add `hours_x_tuition` = study_hours × (tuition == "yes"): does CV improve? (never check on the test set)
"""),
    code("# TODO", stub="# TODO"),

    md("""
## ✅ Checklist for every prediction project
- [x] Looked at the data: missing values, ranges, shapes, outliers
- [x] Locked a test set before modelling; used it once
- [x] Started from a baseline
- [x] Hunted leaks: *does this column exist at prediction time?*
- [x] All preparation inside a pipeline
- [x] Compared models with the same CV folds and score
- [x] Reported the test score with a range
- [x] Read the worst mistakes
- [x] Checked which clues matter
- [x] Saved the pipeline; check inputs before trusting a prediction
"""),
]

# ---------------------------------------------------------------- Lab 2 · classification
NOTEBOOKS["02-classification"] = [
    md("""
# Lab 2 · Classification: who will drop out?
**Goal:** at week 6, give each student a **probability** of dropping out, and decide whom teachers should call.

**You will practise**
- Handle a rare “yes” (11%)
- Stratified splits
- See why accuracy lies
- Find and remove a leak
- Compare models by ranking and by honest probabilities
- Check calibration
- Choose the cut-off from costs, not 0.5
- Use a capacity rule (“we can make 100 calls”)
- Test once with a range, read the missed cases
- Save the model **with** its cut-off

**How to work:** 🧠 = write your guess first · ✓ = the notebook proves the result
"""),
    md("""
## 0 · Setup
"""),
    code("""import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, average_precision_score, brier_score_loss,
                             confusion_matrix, precision_recall_curve, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 0
warnings.filterwarnings("ignore", category=FutureWarning)
plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.grid": True, "font.size": 12})
print("pandas", pd.__version__, "· scikit-learn", sklearn.__version__)"""),

    md("""
## 1 · Load and look
- 3,000 students, all clues known at **week 6**
- Target: `dropped_out` (known at term end)
- Missing file? Run `python make_data.py`
"""),
    code("""df = pd.read_csv("data/dropout.csv")
print(df.shape)
df.head()"""),
    code("""print("missing:", df.isna().sum()[df.isna().sum() > 0].to_dict())
print(f"dropout rate: {df['dropped_out'].mean():.1%}  ({df['dropped_out'].sum()} of {len(df)})")"""),
    code("""fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
for ax, col in zip(axes, ["attendance_wk6", "assignments_submitted", "logins_per_week"]):
    df.boxplot(column=col, by="dropped_out", ax=ax); ax.set_title(col); ax.set_xlabel("dropped out (0 = no, 1 = yes)")
plt.suptitle(""); plt.tight_layout(); plt.show()
print(df.groupby("part_time_job")["dropped_out"].mean().round(3).to_dict(), "← dropout rate by part-time job")"""),
    md("""
**What to notice**
- Dropouts attended less, handed in less, logged in less
- A part-time job more than doubles the risk
- Lots of overlap: no single clue decides
"""),

    md("""
## 2 · 🧠 Predict first
- A lazy model says “nobody drops out”
- Its accuracy? How many dropouts does it catch?
"""),
    code("""my_guess = {"accuracy": 0.89, "dropouts_caught": 0}""", stub="""my_guess = {"accuracy": None, "dropouts_caught": None}"""),

    md("""
## 3 · Lock away a stratified test set
- A rare “yes” can end up unevenly split by chance
- `stratify=y` keeps the same dropout rate in both piles
"""),
    code("""target = "dropped_out"
X = df.drop(columns=[target, "student_id"])
y = df[target]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
print(f"train {len(X_train)} (rate {y_train.mean():.1%}) · test {len(X_test)} (rate {y_test.mean():.1%}, {y_test.sum()} dropouts) – locked")"""),

    md("""
## 4 · Baseline: accuracy lies
"""),
    code("""cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
lazy = DummyClassifier(strategy="most_frequent")
lazy_acc = cross_val_score(lazy, X_train, y_train, cv=cv).mean()
lazy_recall = cross_val_score(lazy, X_train, y_train, cv=cv, scoring="recall").mean()
print(f"'nobody drops out': accuracy {lazy_acc:.1%} · dropouts caught (recall) {lazy_recall:.0%}")
assert lazy_acc > 0.88 and lazy_recall == 0
print("✓ 89% accurate and completely useless: with a rare yes, never judge by accuracy")"""),
    md("""
**Which score, then?**
- **PR-AUC:** how well the rare “yes” is ranked first; lazy ≈ 0.11 (main score)
- **ROC-AUC:** chance a dropout ranks above a stayer; 0.5 = coin flip
- **Brier:** squared error of the probabilities; lower = more honest
"""),

    md("""
## 5 · 🧠 Leak hunt: `exit_survey_done`
- How good does a model with only this column look?
"""),
    code("""survey_only = Pipeline([("prep", ColumnTransformer([("s", OneHotEncoder(), ["exit_survey_done"])])),
                        ("model", LogisticRegression())])
print(f"exit survey only: PR-AUC {cross_val_score(survey_only, X_train, y_train, cv=cv, scoring='average_precision').mean():.2f}  (lazy ≈ {y_train.mean():.2f})")"""),
    md("""
**Too good to be true**
- The exit survey is filled in **after** a student leaves
- At week 6 it doesn't exist: a leak, drop it
"""),
    code("""X_train = X_train.drop(columns="exit_survey_done"); X_test = X_test.drop(columns="exit_survey_done")
print("✓ leak removed:", list(X_train.columns))"""),

    md("""
## 6 · Pipeline
- Numbers: median for missing quiz scores **plus** a 0/1 “was missing” column (no quiz score is itself a warning), then standardise
- Categories: one-hot
"""),
    code("""numeric = ["attendance_wk6", "assignments_submitted", "quiz_avg", "logins_per_week", "distance_km"]
categorical = ["stream", "part_time_job", "scholarship"]

def make_prep():
    return ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), numeric),
        ("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), categorical),
    ])

make_prep().fit(X_train).get_feature_names_out()"""),

    md("""
## 7 · 🧠 Compare models
- Logistic regression
- Logistic with `class_weight="balanced"` (pretends dropouts are as common as stayers)
- Random forest, boosting
- Which ranks best?
"""),
    code("""my_best = "logistic\"""", stub="""my_best = None   # which model will have the best PR-AUC?"""),
    code("""candidates = {
    "logistic": LogisticRegression(max_iter=1000),
    "logistic balanced": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "random forest": RandomForestClassifier(400, min_samples_leaf=5, random_state=SEED, n_jobs=-1),
    "boosting": HistGradientBoostingClassifier(random_state=SEED),
}
rows, cv_probs = {}, {}
for name, model in candidates.items():
    pipe = Pipeline([("prep", make_prep()), ("model", model)])
    p = cross_val_predict(pipe, X_train, y_train, cv=cv, method="predict_proba")[:, 1]   # out-of-fold probabilities
    cv_probs[name] = p
    rows[name] = {"PR-AUC": average_precision_score(y_train, p), "ROC-AUC": roc_auc_score(y_train, p),
                  "Brier": brier_score_loss(y_train, p), "recall @ 0.5": ((p >= 0.5) & (y_train == 1)).sum() / y_train.sum()}
table = pd.DataFrame(rows).T.sort_values("PR-AUC", ascending=False)
table.round(3)""",
         stub="""candidates = {
    "logistic": LogisticRegression(max_iter=1000),
    # TODO: "logistic balanced", "random forest", "boosting"
}
# TODO: for each, get out-of-fold probabilities with cross_val_predict(..., method="predict_proba")
# and compute PR-AUC, ROC-AUC, Brier and recall at 0.5"""),
    code("""assert table.index[0] == "logistic" and table.loc["logistic", "PR-AUC"] > 2 * y_train.mean()
print("✓ plain logistic regression ranks best and its probabilities are the most honest (lowest Brier)")"""),
    md("""
**Read the table**
- All rank far better than chance, but at cut-off 0.5 most catch **under a third** of dropouts
- “Balanced”: same ranking, **inflated** probabilities (worse Brier)
- Better: keep honest probabilities and **choose the cut-off on purpose**
"""),

    md("""
## 8 · Are the probabilities honest?
- Group students by predicted probability
- Did that share really drop out?
"""),
    code("""p_cv = cv_probs["logistic"]
true_rate, predicted = calibration_curve(y_train, p_cv, n_bins=6, strategy="quantile")
plt.plot([0, 0.6], [0, 0.6], "--", c="grey", label="perfectly honest")
plt.plot(predicted, true_rate, "o-", label="logistic")
plt.xlabel("predicted probability"); plt.ylabel("real dropout rate"); plt.legend(); plt.show()
print(pd.DataFrame({"predicted": predicted, "real": true_rate}).round(2).to_string(index=False))"""),
    md("""
**Calibrated**
- Dots on the diagonal: “40%” really means about 40%
- Honest probabilities let us reason about costs
"""),

    md("""
## 9 · 🧠 Choose the cut-off from costs
- A teacher's call costs **1**
- A missed dropout costs **10**
- Should the cut-off be above or below 0.5?
"""),
    code("""my_cutoff_guess = 0.1""", stub="""my_cutoff_guess = None"""),
    code("""COST_MISS, COST_CALL = 10, 1
cutoffs = np.round(np.arange(0.02, 0.81, 0.01), 2)
def total_cost(y_true, p, t):
    missed = ((p < t) & (y_true == 1)).sum()
    calls = (p >= t).sum()
    return COST_MISS * missed + COST_CALL * calls
costs = [total_cost(y_train.to_numpy(), p_cv, t) for t in cutoffs]
CUTOFF = float(cutoffs[int(np.argmin(costs))])
plt.plot(cutoffs, costs); plt.axvline(CUTOFF, c="green", ls="--", label=f"cheapest: {CUTOFF}"); plt.axvline(0.5, c="red", ls=":", label="default 0.5")
plt.xlabel("cut-off"); plt.ylabel("total cost (training, out-of-fold)"); plt.legend(); plt.show()
print(f"cheapest cut-off {CUTOFF} · cost {min(costs)} vs {total_cost(y_train.to_numpy(), p_cv, 0.5)} at 0.5")"""),
    code("""for t in (0.5, CUTOFF):
    tn, fp, fn, tp = confusion_matrix(y_train, p_cv >= t).ravel()
    print(f"cut-off {t:<4}: caught {tp}/{tp + fn} dropouts (recall {tp / (tp + fn):.0%}) · calls {tp + fp} · precision {tp / (tp + fp):.0%}")
assert CUTOFF < 0.2
print("✓ when missing a dropout costs 10× a call, the best cut-off is far below 0.5")"""),
    md("""
**Notice**
- The cost curve is flat near its minimum
- The exact cut-off matters less than **not using 0.5**
"""),

    md("""
## 10 · Capacity rule: only 100 calls
- When time is the limit, call the 100 highest-risk students
- Ranking quality (PR-AUC) is what matters here
"""),
    code("""top = np.argsort(-p_cv)[:100]
caught = y_train.to_numpy()[top].sum()
random_caught = 100 * y_train.mean()
print(f"top-100 by risk catch {caught} dropouts · 100 random students would catch ≈ {random_caught:.0f}")
assert caught > 4 * random_caught
print(f"✓ ranking by risk finds {caught / random_caught:.1f}× more dropouts than calling at random")"""),

    md("""
## 11 · Final test: once
- Train on all training students
- Score the locked test set with the chosen cut-off
- Give a range for recall
"""),
    code("""final = Pipeline([("prep", make_prep()), ("model", LogisticRegression(max_iter=1000))]).fit(X_train, y_train)
p_test = final.predict_proba(X_test)[:, 1]
flag = p_test >= CUTOFF
tn, fp, fn, tp = confusion_matrix(y_test, flag).ravel()
recall, precision = tp / (tp + fn), tp / (tp + fp)

rng = np.random.default_rng(SEED); yt = y_test.to_numpy(); boot = []
for _ in range(3000):
    i = rng.integers(0, len(yt), len(yt)); boot.append((flag[i] & (yt[i] == 1)).sum() / max(1, (yt[i] == 1).sum()))
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"test: caught {tp} of {tp + fn} dropouts · recall {recall:.0%} (95% range {lo:.0%}–{hi:.0%}) · precision {precision:.0%} · calls {tp + fp}")
print(f"PR-AUC {average_precision_score(y_test, p_test):.2f} · ROC-AUC {roc_auc_score(y_test, p_test):.2f} · accuracy at 0.5 {((p_test >= 0.5) == y_test).mean():.1%} (lazy {1 - y_test.mean():.1%})")
ConfusionMatrixDisplay.from_predictions(y_test, flag, display_labels=["stays", "drops out"], cmap="Blues"); plt.title(f"Test set, cut-off {CUTOFF}"); plt.show()"""),
    code("""recall_at_half = ((p_test >= 0.5) & (yt == 1)).sum() / yt.sum()
print(f"same model, default cut-off 0.5: recall {recall_at_half:.0%}")
assert lo > recall_at_half
print(f"✓ proof: on students never seen we catch {recall:.0%} of dropouts (at least {lo:.0%} likely) vs {recall_at_half:.0%} at 0.5, calling {tp + fp} of {len(yt)} students")"""),

    md("""
## 12 · Read the missed dropouts
- What do they look like?
"""),
    code("""missed = X_test[(~flag) & (y_test == 1)].assign(p=p_test[(~flag) & (y_test == 1)].round(3))
print(f"{len(missed)} missed dropouts; typical profile vs all dropouts:")
pd.DataFrame({"missed": missed[numeric].median(), "all dropouts": X_test[y_test == 1][numeric].median()}).round(1)"""),
    md("""
**What the misses say**
- They look like ordinary students at week 6
- The reason they left isn't in the data (family, money, health)
- To catch them: **new clues**, not a fancier model
"""),

    md("""
## 13 · Explain: which clues raise the risk?
- Each weight = change in log-odds per standard deviation (numbers) or for that category
"""),
    code("""weights = pd.Series(final.named_steps["model"].coef_[0], index=final.named_steps["prep"].get_feature_names_out()).sort_values()
weights.plot.barh(color=np.where(weights > 0, "#C2412D", "#2E7D5B")); plt.xlabel("← lowers risk · raises risk →"); plt.show()
assert weights.idxmin().endswith("attendance_wk6") and weights.idxmax().endswith("part_time_job_yes")
print("✓ low attendance and a part-time job raise the risk most; a scholarship lowers it")"""),

    md("""
## 14 · Save the model **with its cut-off**
"""),
    code("""Path("models").mkdir(exist_ok=True)
joblib.dump({"pipeline": final, "cutoff": CUTOFF, "cost_ratio": f"{COST_MISS}:{COST_CALL}"}, "models/dropout_model.joblib")

saved = joblib.load("models/dropout_model.joblib")
def assess(student: dict) -> dict:
    p = float(saved["pipeline"].predict_proba(pd.DataFrame([student]))[0, 1])
    return {"risk": round(p, 3), "call": p >= saved["cutoff"]}

ravi = {"stream": "arts", "attendance_wk6": 62, "assignments_submitted": 55, "quiz_avg": 48,
        "logins_per_week": 2, "distance_km": 18, "part_time_job": "yes", "scholarship": "no"}
neha = {"stream": "science", "attendance_wk6": 94, "assignments_submitted": 95, "quiz_avg": 78,
        "logins_per_week": 7, "distance_km": 4, "part_time_job": "no", "scholarship": "yes"}
print("Ravi:", assess(ravi), "· Neha:", assess(neha))
assert assess(ravi)["call"] and not assess(neha)["call"]
print("✓ the saved model flags Ravi for a call and leaves Neha alone")"""),

    md("""
## 15 · Your turn
- Cost ratio 5:1 and 20:1: how do cut-off, recall and calls change?
- 150 calls: how many test dropouts does the top-150 catch?
- Add `job_and_low_attendance` (job AND attendance < 70): does CV PR-AUC improve?
"""),
    code("# TODO", stub="# TODO"),

    md("""
## ✅ Checklist for every classification project
- [x] Measured how rare the “yes” is; stratified every split
- [x] Started from a lazy baseline; didn't judge by accuracy
- [x] Hunted leaks: *does this column exist at prediction time?*
- [x] Compared models by ranking (PR-AUC) and honesty (Brier), out-of-fold
- [x] Checked calibration
- [x] Chose the cut-off from costs (or capacity), on training data only
- [x] Tested once, with a range
- [x] Read the missed cases
- [x] Explained the weights
- [x] Saved the pipeline with its cut-off
"""),
]

# ---------------------------------------------------------------- Lab 3 · neural network
NOTEBOOKS["03-neural-network"] = [
    md("""
# Lab 3 · Neural network: recognise handwritten digits
**Goal:** read a handwritten digit (0–9) from an 8×8 image, and know when not to trust the answer.

**You will practise**
- Scale inputs; train / validation / test split
- Start from a simple baseline
- Build, compile and train a Keras model
- Read learning curves; spot overfitting
- Fix it: early stopping, dropout
- Use a model built for images (CNN)
- Compare on validation; test once
- Read the mistakes; use confidence to hand hard cases to a human
- Save, reload, predict

**How to work:** 🧠 = write your guess first · ✓ = the notebook proves the result
"""),
    md("""
## 0 · Setup
- Fix all random seeds (NumPy, Python, TensorFlow) with one call
- Small data: runs on a laptop CPU in about a minute
"""),
    code("""import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from pathlib import Path

import keras
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split

SEED = 0
keras.utils.set_random_seed(SEED)
plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.grid": True, "font.size": 12})
print("keras", keras.__version__, "· backend", keras.backend.backend())"""),

    md("""
## 1 · Load and look
- 1,797 images, 8×8 pixels, values 0–16
- Target: the digit 0–9
"""),
    code("""digits = load_digits()
images, labels = digits.images, digits.target
print(images.shape, "· classes:", np.bincount(labels))
fig, axes = plt.subplots(2, 10, figsize=(12, 2.8))
for ax, img, lab in zip(axes.ravel(), images, labels):
    ax.imshow(img, cmap="gray_r"); ax.set_title(lab); ax.axis("off")
plt.tight_layout(); plt.show()"""),
    md("""
**What to notice**
- Classes are balanced (≈ 180 each): accuracy is a fair score here
- Low resolution: some 1s, 7s and 9s look alike
"""),

    md("""
## 2 · Scale and split
- Scale pixels to 0–1 (neural networks train best on small, similar-sized inputs)
- Three piles, stratified: train 60% · validation 20% (compare, tune, stop) · test 20% (locked, used once)
"""),
    code("""X = (images / 16.0).astype("float32")
y = labels
X_trval, X_test, y_trval, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
X_train, X_val, y_train, y_val = train_test_split(X_trval, y_trval, test_size=0.25, stratify=y_trval, random_state=SEED)
print(f"train {len(X_train)} · validation {len(X_val)} · test {len(X_test)} (locked)")"""),

    md("""
## 3 · 🧠 Predict first
- Logistic regression on the 64 raw pixels: what validation accuracy?
- Can a neural network do better?
"""),
    code("""my_guess = {"logistic": 0.90, "best_network": 0.98}""", stub="""my_guess = {"logistic": None, "best_network": None}"""),

    md("""
## 4 · Baseline: logistic regression
- 64 pixels in a row, one weight per pixel per digit
- Every network must beat this
"""),
    code("""flat = lambda a: a.reshape(len(a), -1)
logistic = LogisticRegression(max_iter=2000).fit(flat(X_train), y_train)
baseline_acc = logistic.score(flat(X_val), y_val)
print(f"logistic regression: validation accuracy {baseline_acc:.1%}")"""),

    md("""
## 5 · A first network
- Flatten → Dense(64, ReLU) → Dense(10, softmax)
- Loss: sparse categorical cross-entropy (labels are integers 0–9)
- Optimiser: Adam, learning rate 0.001
- Always pass validation data to `fit` to watch it learn
"""),
    code("""def train(model, epochs, callbacks=(), name=""):
    \"\"\"Compile, train with validation, return the history as a DataFrame.\"\"\"
    keras.utils.set_random_seed(SEED)
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    h = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=epochs, batch_size=32, verbose=0, callbacks=list(callbacks))
    hist = pd.DataFrame(h.history); hist.index += 1
    print(f"{name}: {len(hist)} epochs · params {model.count_params():,} · val accuracy {model.evaluate(X_val, y_val, verbose=0)[1]:.1%} · best val loss {hist.val_loss.min():.3f}")
    return hist

def small_dense():
    return keras.Sequential([keras.Input((8, 8)), keras.layers.Flatten(),
                             keras.layers.Dense(64, activation="relu"), keras.layers.Dense(10, activation="softmax")], name="small_dense")

keras.utils.set_random_seed(SEED)
small = small_dense()
small.summary()
hist_small = train(small, 100, name="small dense")""",
         stub="""def train(model, epochs, callbacks=(), name=""):
    \"\"\"Compile, train with validation, return the history as a DataFrame.\"\"\"
    keras.utils.set_random_seed(SEED)
    # TODO: model.compile(Adam(1e-3), sparse_categorical_crossentropy, metrics=["accuracy"])
    # TODO: h = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=epochs, batch_size=32, verbose=0, callbacks=list(callbacks))
    ...

# TODO: small = Sequential([Input((8, 8)), Flatten(), Dense(64, relu), Dense(10, softmax)]); hist_small = train(small, 100)"""),

    md("""
## 6 · Learning curves
- Training loss should fall
- Validation loss falls, then flattens: that's where learning stops paying off
"""),
    code("""def plot_curves(hist, title):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 3.8))
    hist[["loss", "val_loss"]].plot(ax=a, title=f"{title}: loss"); a.set_xlabel("epoch")
    hist[["accuracy", "val_accuracy"]].plot(ax=b, title=f"{title}: accuracy", ylim=(0.8, 1.01)); b.set_xlabel("epoch")
    plt.tight_layout(); plt.show()

plot_curves(hist_small, "small dense")"""),

    md("""
## 7 · 🧠 A much bigger network, trained for longer
- Two layers of 512 neurons (≈ 300,000 weights for 1,077 images), 200 epochs, no protection
- What happens to the validation loss?
"""),
    code("""def big_dense(dropout=0.0):
    layers = [keras.Input((8, 8)), keras.layers.Flatten()]
    for _ in range(2):
        layers.append(keras.layers.Dense(512, activation="relu"))
        if dropout: layers.append(keras.layers.Dropout(dropout))
    return keras.Sequential(layers + [keras.layers.Dense(10, activation="softmax")])

hist_big = train(big_dense(), 200, name="big, no protection")
plot_curves(hist_big, "big, no protection")"""),
    code("""best_epoch = int(hist_big.val_loss.idxmin())
print(f"val loss: best {hist_big.val_loss.min():.3f} at epoch {best_epoch} → {hist_big.val_loss.iloc[-1]:.3f} at the end · train accuracy {hist_big.accuracy.iloc[-1]:.0%}")
assert hist_big.val_loss.iloc[-1] > 1.3 * hist_big.val_loss.min() and hist_big.accuracy.iloc[-1] == 1.0
print("✓ overfitting: training is perfect while validation loss climbs after its best epoch")"""),
    md("""
**Overfitting**
- The network memorises the training images
- Validation loss climbs back up, even while accuracy looks fine
- Watch the **loss**, not only accuracy: it shows the network growing over-confident
"""),

    md("""
## 8 · Fix it: early stopping and dropout
- **Early stopping:** stop when validation loss hasn't improved for 15 epochs; keep the best weights
- **Dropout:** switch off a random 40% of neurons at every training step, so no neuron can be relied on alone
"""),
    code("""stop = lambda: keras.callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True)
hist_es = train(big_dense(), 300, [stop()], name="big + early stopping")
hist_drop = train(big_dense(dropout=0.4), 300, [stop()], name="big + dropout + early stopping")
plot_curves(hist_drop, "big + dropout + early stopping")""",
         stub="""stop = lambda: keras.callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True)
# TODO: train big_dense() with [stop()] for up to 300 epochs → hist_es
# TODO: train big_dense(dropout=0.4) with [stop()] → hist_drop"""),
    code("""assert len(hist_es) < 100 and hist_drop.val_loss.min() < hist_big.val_loss.min()
print(f"✓ early stopping ended after {len(hist_es)} of 300 epochs; dropout reached a lower validation loss ({hist_drop.val_loss.min():.3f} vs {hist_big.val_loss.min():.3f})")"""),

    md("""
## 9 · A network built for images: CNN
- **Convolution:** small 3×3 filters slide over the image and detect strokes and corners anywhere
- **Pooling:** shrink the map, keep the strongest signals
- Far fewer weights than the big dense network, because each filter is reused everywhere
"""),
    code("""def cnn():
    return keras.Sequential([
        keras.Input((8, 8, 1)),
        keras.layers.Conv2D(32, 3, padding="same", activation="relu"),
        keras.layers.Conv2D(32, 3, padding="same", activation="relu"),
        keras.layers.MaxPooling2D(),
        keras.layers.Flatten(),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dense(10, activation="softmax"),
    ], name="cnn")

hist_cnn = train(cnn(), 300, [stop()], name="CNN + dropout + early stopping")
plot_curves(hist_cnn, "CNN")"""),

    md("""
## 10 · Compare on validation
- Accuracy differences are small; validation **loss** shows how confident and right each model is
"""),
    code("""final_val = lambda h: h.loc[h.val_loss.idxmin()]
summary = pd.DataFrame({
    "logistic regression": {"val accuracy": baseline_acc, "val loss": np.nan},
    "small dense": {"val accuracy": final_val(hist_small).val_accuracy, "val loss": hist_small.val_loss.min()},
    "big, no protection": {"val accuracy": hist_big.val_accuracy.iloc[-1], "val loss": hist_big.val_loss.iloc[-1]},
    "big + dropout + ES": {"val accuracy": final_val(hist_drop).val_accuracy, "val loss": hist_drop.val_loss.min()},
    "CNN": {"val accuracy": final_val(hist_cnn).val_accuracy, "val loss": hist_cnn.val_loss.min()},
}).T
summary.round(3)"""),
    code("""assert summary["val loss"].idxmin() == "CNN" and summary.loc["CNN", "val accuracy"] > baseline_acc
print(f"✓ the CNN wins: lowest validation loss, and {summary.loc['CNN', 'val accuracy']:.1%} vs {baseline_acc:.1%} for logistic regression")"""),

    md("""
## 11 · Final test: once
- Retrain the chosen CNN exactly as before (same seed, same early stopping)
- Score the locked test set one time; give a range
"""),
    code("""keras.utils.set_random_seed(SEED)
model = cnn()
_ = train(model, 300, [stop()], name="final CNN")
probs = model.predict(X_test, verbose=0)
pred = probs.argmax(axis=1)
correct = pred == y_test

rng = np.random.default_rng(SEED)
boot = [correct[rng.integers(0, len(correct), len(correct))].mean() for _ in range(5000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"test accuracy {correct.mean():.1%} (95% range {lo:.1%}–{hi:.1%}) · {(~correct).sum()} mistakes of {len(y_test)}")
assert correct.mean() >= 0.97
print("✓ proof: the CNN reads at least 97% of digits it has never seen")"""),

    md("""
## 12 · Read the mistakes
- Which digits get confused?
- Look at the images it got wrong: would you have got them right?
"""),
    code("""ConfusionMatrixDisplay.from_predictions(y_test, pred, cmap="Blues", colorbar=False); plt.title("Test set"); plt.show()
wrong = np.where(~correct)[0]
fig, axes = plt.subplots(1, len(wrong), figsize=(1.6 * len(wrong), 2.2))
for ax, i in zip(np.atleast_1d(axes), wrong):
    ax.imshow(X_test[i], cmap="gray_r"); ax.set_title(f"true {y_test[i]}\\nsaid {pred[i]} ({probs[i].max():.0%})", fontsize=10); ax.axis("off")
plt.tight_layout(); plt.show()"""),

    md("""
## 13 · 🧠 Use confidence: let a human check the hard ones
- The softmax output is a probability for each digit
- Rule: accept the answer only if its probability ≥ 0.9; otherwise send to a person
- Predict: what share needs a person? How accurate are the accepted ones?
"""),
    code("""THRESHOLD = 0.9
confident = probs.max(axis=1) >= THRESHOLD
print(f"sent to a person: {(~confident).mean():.1%} · accuracy on the rest: {correct[confident].mean():.1%} (all: {correct.mean():.1%})")
print(f"mistakes caught by the rule: {(~correct & ~confident).sum()} of {(~correct).sum()}")
assert correct[confident].mean() >= correct.mean()
print("✓ low-confidence answers hold most of the mistakes: checking a few cases buys a lot of accuracy")"""),

    md("""
## 14 · Save, reload, predict
- Save the whole model (architecture + weights) in one `.keras` file
- Reload and check it gives identical predictions
"""),
    code("""Path("models").mkdir(exist_ok=True)
model.save("models/digits_cnn.keras")
loaded = keras.models.load_model("models/digits_cnn.keras")
assert np.allclose(loaded.predict(X_test, verbose=0), probs, atol=1e-6)

def read_digit(image_0_to_16):
    \"\"\"8×8 array with values 0–16 → (digit, probability, needs_human).\"\"\"
    p = loaded.predict((np.asarray(image_0_to_16, "float32") / 16.0)[None], verbose=0)[0]
    return int(p.argmax()), round(float(p.max()), 3), bool(p.max() < THRESHOLD)

print("first test image:", read_digit(X_test[0] * 16), "· true", y_test[0])
print("✓ the reloaded model gives identical predictions")"""),

    md("""
## 15 · Your turn
- Change the dropout rate to 0 and 0.6 in the CNN: what happens to validation loss?
- Try learning rate 0.01 and 0.0001: how do the learning curves change?
- Shift every test image one pixel right (`np.roll(X_test, 1, axis=2)`): which drops more, the CNN or the small dense network?
"""),
    code("# TODO", stub="# TODO"),

    md("""
## ✅ Checklist for every neural-network project
- [x] Scaled inputs; split train / validation / test, stratified
- [x] Beat a simple baseline first
- [x] Watched learning curves (loss, not only accuracy)
- [x] Recognised overfitting; used early stopping and dropout
- [x] Picked an architecture that fits the data (CNN for images)
- [x] Compared on validation; tested once, with a range
- [x] Read the mistakes
- [x] Used confidence to route hard cases to a person
- [x] Fixed seeds; saved and reloaded the model, checked identical output
"""),
]

# ---------------------------------------------------------------- Lab 4 · text classification
NOTEBOOKS["04-text-classification"] = [
    md("""
# Lab 4 · Text classification: sort forum posts by topic
**Goal:** read a post and say which of 6 topics it belongs to; know which posts we can't classify.

**You will practise**
- Real text data: look at lengths, empties, examples
- Find a leak hidden in text (headers, signatures)
- Respect time: the test set is later than the training set
- Classic baseline: TF-IDF + logistic regression, tuned with CV
- Explain it: the words that drive each topic
- Pretrained sentence embeddings (MiniLM)
- Learn from very few labels
- Read mistakes, measure by text length, save and use

**How to work:** 🧠 = write your guess first · ✓ = the notebook proves the result
"""),
    md("""
## 0 · Setup
- First run downloads the dataset (≈ 14 MB) and MiniLM (≈ 90 MB); later runs use the cache
"""),
    code("""import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline

SEED = 0
warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.grid": True, "font.size": 12})
TOPICS = ["comp.graphics", "rec.autos", "rec.sport.hockey", "sci.med", "sci.space", "talk.politics.guns"]
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)"""),

    md("""
## 1 · Load the raw posts and look
- 20 Newsgroups: real forum posts from the 1990s; we use 6 topics
- The official test set was posted **later** than the training set
"""),
    code("""def load(remove=()):
    kw = dict(categories=TOPICS, remove=remove, random_state=SEED)
    return fetch_20newsgroups(subset="train", **kw), fetch_20newsgroups(subset="test", **kw)

raw_train, raw_test = load()
names = raw_train.target_names
print(f"train {len(raw_train.data)} posts · test {len(raw_test.data)} posts · topics {names}")
print(pd.Series(raw_train.target).map(dict(enumerate(names))).value_counts().to_dict())
print("\\n--- one raw post ---\\n", raw_train.data[0][:700])"""),
    md("""
**What to notice**
- Each post starts with **headers**: sender, email, organisation, subject
- Many end with a **signature**, and quote earlier posts
- Classes are roughly balanced
"""),

    md("""
## 2 · 🧠 Leak hunt
- Train TF-IDF + logistic regression on the raw posts, then on posts with headers, signatures and quotes removed
- Which scores higher? Which number would you believe?
"""),
    code("""my_guess = {"raw": 0.95, "cleaned": 0.85}""", stub="""my_guess = {"raw": None, "cleaned": None}"""),
    code("""def tfidf_model(C=10):
    return make_pipeline(TfidfVectorizer(sublinear_tf=True, min_df=2), LogisticRegression(C=C, max_iter=3000))

train, test = load(remove=("headers", "footers", "quotes"))
scores = {}
for label, (tr, te) in {"raw": (raw_train, raw_test), "cleaned": (train, test)}.items():
    m = tfidf_model().fit(tr.data, tr.target)
    scores[label] = {"CV": cross_val_score(tfidf_model(), tr.data, tr.target, cv=cv).mean(), "test": m.score(te.data, te.target)}
pd.DataFrame(scores).T.round(3)"""),
    code("""assert scores["raw"]["test"] > scores["cleaned"]["test"] + 0.05
print("✓ headers and signatures inflate the score: they name the sender, not the topic")"""),
    md("""
**Why it's a leak**
- The same people post in the same groups: names, emails and signatures give the answer away
- A new post from a new person has none of that
- Always train on what the model will really see: the cleaned text
"""),

    md("""
## 3 · Clean data: empties and lengths
"""),
    code("""lengths = pd.Series([len(t.split()) for t in train.data])
empty_train = int((lengths == 0).sum()); empty_test = sum(len(t.split()) == 0 for t in test.data)
print(f"empty after cleaning: train {empty_train} · test {empty_test} · median words {lengths.median():.0f}")
lengths.clip(upper=600).plot.hist(bins=40); plt.xlabel("words per post (clipped at 600)"); plt.show()

keep = lengths.to_numpy() > 0                      # drop empty posts from TRAINING only
X_train = [t for t, k in zip(train.data, keep) if k]; y_train = train.target[keep]
X_test, y_test = test.data, test.target            # never drop from the test set: real life sends empties too
print(f"training on {len(X_train)} posts")"""),

    md("""
## 4 · Baseline: TF-IDF + logistic regression, tuned
- **TF-IDF:** one column per word; weight = how often in this post × how rare overall
- Tune with cross-validation on the training set only
"""),
    code("""grid = GridSearchCV(
    make_pipeline(TfidfVectorizer(sublinear_tf=True), LogisticRegression(max_iter=3000)),
    {"tfidfvectorizer__ngram_range": [(1, 1), (1, 2)], "tfidfvectorizer__min_df": [1, 2], "logisticregression__C": [1, 10, 30]},
    cv=cv, n_jobs=-1)
grid.fit(X_train, y_train)
tfidf = grid.best_estimator_
tfidf_cv, tfidf_test = grid.best_score_, tfidf.score(X_test, y_test)
print(f"best {grid.best_params_}\\nCV {tfidf_cv:.1%} · test {tfidf_test:.1%}")""",
         stub="""# TODO: GridSearchCV over a TfidfVectorizer + LogisticRegression pipeline
# grid: ngram_range (1,1)/(1,2), min_df 1/2, C 1/10/30 · cv=cv
# then tfidf = grid.best_estimator_, tfidf_cv = grid.best_score_, tfidf_test = tfidf.score(X_test, y_test)"""),
    md("""
**CV vs test**
- The test posts were written later: new names, new events, new words
- Expect the test score to sit a little **below** CV: that gap is drift, and it's normal
"""),

    md("""
## 5 · Explain it: the words behind each topic
"""),
    code("""vocab = np.array(tfidf.named_steps["tfidfvectorizer"].get_feature_names_out())
coef = tfidf.named_steps["logisticregression"].coef_
pd.DataFrame({names[k]: vocab[np.argsort(-coef[k])[:8]] for k in range(len(names))})"""),
    md("""
**Check**
- The top words make sense for each topic: the model learned the subject, not the senders
- If you saw names or email domains here, you'd still have a leak
"""),

    md("""
## 6 · 🧠 Pretrained sentence embeddings
- MiniLM turns each post into 384 numbers that capture meaning
- Train only a logistic regression on top
- Predict: better or worse than TF-IDF on the test set?
"""),
    code("""my_embed_guess = "better\"""", stub="""my_embed_guess = None   # "better" or "worse"?"""),
    code("""reader = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
E_train = reader.encode(X_train, batch_size=64, normalize_embeddings=True)
E_test = reader.encode(X_test, batch_size=64, normalize_embeddings=True)
head = LogisticRegression(C=1, max_iter=3000)
embed_cv = cross_val_score(head, E_train, y_train, cv=cv).mean()
head.fit(E_train, y_train)
embed_test = head.score(E_test, y_test)
results = pd.DataFrame({"TF-IDF + logistic": [tfidf_cv, tfidf_test], "MiniLM + logistic": [embed_cv, embed_test]}, index=["CV", "test"]).T
results.round(3)""",
         stub="""reader = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# TODO: E_train / E_test = reader.encode(..., batch_size=64, normalize_embeddings=True)
# TODO: head = LogisticRegression(C=1, max_iter=3000); embed_cv (CV on E_train), fit, embed_test"""),
    code("""assert embed_test > tfidf_test
print(f"✓ pretrained embeddings beat TF-IDF on later posts: {embed_test:.1%} vs {tfidf_test:.1%}")"""),
    md("""
**Why**
- TF-IDF only knows words seen in training
- MiniLM already knows that “engine” and “transmission”, or “orbit” and “launch”, belong together
- That knowledge carries over to posts with new words
"""),

    md("""
## 7 · 🧠 Very few labels
- Labelling is expensive. Train each model on only 10, 30 and 100 posts per topic
- Which model suffers more?
"""),
    code("""rng = np.random.default_rng(SEED)
rows = {}
for n in (10, 30, 100):
    idx = np.concatenate([rng.choice(np.where(y_train == c)[0], n, replace=False) for c in range(len(names))])
    a = tfidf_model().set_params(tfidfvectorizer__min_df=1).fit([X_train[i] for i in idx], y_train[idx]).score(X_test, y_test)
    b = LogisticRegression(C=10, max_iter=3000).fit(E_train[idx], y_train[idx]).score(E_test, y_test)
    rows[f"{n} per topic"] = {"TF-IDF": a, "MiniLM": b}
few = pd.DataFrame(rows).T
few.plot(marker="o", ylim=(0.4, 1)); plt.ylabel("test accuracy"); plt.show()
few.round(3)"""),
    code("""assert few.loc["10 per topic", "MiniLM"] - few.loc["10 per topic", "TF-IDF"] > 0.2
print(f"✓ with 10 labels per topic: MiniLM {few.loc['10 per topic', 'MiniLM']:.0%} vs TF-IDF {few.loc['10 per topic', 'TF-IDF']:.0%}")"""),

    md("""
## 8 · Read the mistakes
- Which topics get confused?
- Accuracy by post length: are short posts the problem?
"""),
    code("""pred = head.predict(E_test); probs = head.predict_proba(E_test)
print(classification_report(y_test, pred, target_names=names, digits=3))
ConfusionMatrixDisplay.from_predictions(y_test, pred, display_labels=[n.split(".")[-1] for n in names], cmap="Blues", colorbar=False, xticks_rotation=45)
plt.show()"""),
    code("""words = np.array([len(t.split()) for t in X_test])
bins = pd.cut(words, [-1, 0, 10, 30, 100, 10_000], labels=["empty", "1–10", "11–30", "31–100", "100+"])
by_len = pd.DataFrame({"correct": pred == y_test, "length": bins}).groupby("length", observed=True)["correct"].agg(["mean", "size"])
by_len.round(3)"""),
    code("""assert by_len.loc["empty", "mean"] < 0.5 and by_len.loc["100+", "mean"] > 0.9
print("✓ long posts are easy; empty and very short posts are guesses")"""),

    md("""
## 9 · 🧠 A rule for posts we can't classify
- Send a post to a person if it has fewer than 5 words **or** the top probability is below 0.5
- Predict: what share goes to a person? Accuracy on the rest?
"""),
    code("""to_person = (words < 5) | (probs.max(axis=1) < 0.5)
acc_rest = (pred == y_test)[~to_person].mean()
print(f"to a person: {to_person.mean():.1%} · accuracy on the rest: {acc_rest:.1%} (all: {(pred == y_test).mean():.1%})")
assert acc_rest > embed_test + 0.04
print("✓ routing the hardest posts to a person lifts accuracy on the rest by several points")"""),

    md("""
## 10 · Save and use
- Save the small head with joblib; record which embedding model it needs
- One function does the whole job: text → topic, probability, needs a person?
"""),
    code("""Path("models").mkdir(exist_ok=True)
joblib.dump({"head": head, "embedder": "sentence-transformers/all-MiniLM-L6-v2", "topics": names}, "models/topic_classifier.joblib")

bundle = joblib.load("models/topic_classifier.joblib")
embedder = SentenceTransformer(bundle["embedder"])
def classify(text):
    p = bundle["head"].predict_proba(embedder.encode([text], normalize_embeddings=True))[0]
    k = int(p.argmax())
    return {"topic": bundle["topics"][k], "p": round(float(p[k]), 2), "needs_person": bool(len(text.split()) < 5 or p[k] < 0.5)}

for t in ["My car engine overheats on the highway. Should I replace the radiator or the thermostat?",
          "NASA plans another shuttle launch next month to repair the telescope.",
          "thanks!"]:
    print(classify(t), "←", t)"""),
    code("""assert classify("My car engine overheats on the highway. Should I replace the radiator or the thermostat?")["topic"] == "rec.autos"
assert classify("thanks!")["needs_person"]
print("✓ the saved classifier sorts new posts and flags ones it can't judge")"""),

    md("""
## 11 · Your turn
- Add `"comp.windows.x"` as a 7th topic: which topic does it get confused with?
- Try MiniLM + TF-IDF together (stack the two feature sets): does it beat both?
- Change the person rule to probability < 0.7: how many go to a person now?
"""),
    code("# TODO", stub="# TODO"),

    md("""
## ✅ Checklist for every text-classification project
- [x] Read real examples; checked lengths and empty texts
- [x] Removed text that leaks the answer (headers, signatures, IDs)
- [x] Kept the time order: trained on older, tested on newer
- [x] Tuned a TF-IDF baseline with cross-validation
- [x] Checked the top words make sense
- [x] Tried pretrained embeddings, especially with few labels
- [x] Read mistakes by topic and by length
- [x] Routed short or unsure texts to a person
- [x] Saved the model with the name of the embedder it needs
"""),
]


if __name__ == "__main__":
    paths = [build(name, cells) for name, cells in NOTEBOOKS.items()]
    print(f"wrote {len(paths)} solution notebook(s) + starters")
    if "--run" in sys.argv:
        failed = []
        for p in paths:
            r = subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(p)], capture_output=True, text=True)
            print(("✓ " if r.returncode == 0 else "✗ ") + p.name)
            if r.returncode:
                failed.append(p.name); print(r.stderr[-1500:])
        sys.exit(1 if failed else 0)
