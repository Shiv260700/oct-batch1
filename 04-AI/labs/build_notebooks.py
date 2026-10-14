"""
Builds the lab notebooks for the AI training (education domain: Asha and her class).

Each notebook is written twice from one source:
  labs/<name>.ipynb          solution (the trainer's live demo; every cell filled in)
  labs/starter/<name>.ipynb  starter  (participants; solution cells replaced by TODO stubs)

Every notebook follows docs/lab-notebook-standard.md:
  objectives → your prediction → the idea → the math → by hand → NumPy → PROOF (asserts the slide numbers)
  → picture → break it → your turn → recap.

Run:  .venv/bin/python build_notebooks.py          (writes notebooks)
      .venv/bin/python build_notebooks.py --run    (also executes every solution notebook to prove it runs)
"""
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
SETUP = """import numpy as np
import matplotlib.pyplot as plt
np.set_printoptions(precision=3, suppress=True)
plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.grid": True, "font.size": 12})"""


def md(text):
    return ("md", text.strip("\n"), None)


def code(text, stub=None):
    """A code cell. If `stub` is given, the starter notebook shows the stub instead of the solution."""
    return ("code", text.strip("\n"), None if stub is None else stub.strip("\n"))


def build(name, cells):
    for variant in ("solution", "starter"):
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        for kind, text, stub in cells:
            if kind == "md":
                nb.cells.append(nbf.v4.new_markdown_cell(text))
            else:
                src = stub if (variant == "starter" and stub is not None) else text
                cell = nbf.v4.new_code_cell(src)
                if stub is not None:
                    cell.metadata["tags"] = ["solution"] if variant == "solution" else ["todo"]
                nb.cells.append(cell)
        out = HERE / (f"{name}.ipynb" if variant == "solution" else f"starter/{name}.ipynb")
        out.parent.mkdir(exist_ok=True)
        nbf.write(nb, out)
    return HERE / f"{name}.ipynb"


NOTEBOOKS = {}

# ---------------------------------------------------------------- Chapter 2
NOTEBOOKS["ch02-rules-vs-learning"] = [
    md("""
# Chapter 2 · Rules vs learning
**Deck 1 · Live demo.** Write the teacher’s rule as code, count its mistakes, then let a loop find a better rule from last term’s data.

**You will:** turn a rule into a function · count mistakes · search every threshold · prove the slide numbers (5, 4, 3, 0).
"""),
    code(SETUP),
    md("## 1 · Your prediction\nThe school’s rule: **at risk if attendance is below 75%**. Last term had 8 students: 4 passed, 4 failed. How many will the rule get wrong?"),
    code("my_prediction_mistakes = 5   # ← your guess", stub="my_prediction_mistakes = None   # ← your guess"),
    md("## 2 · Last term’s class"),
    code("""names      = ['Ravi', 'Meena', 'Kiran', 'Leela', 'Arjun', 'Sara', 'Dev', 'Priya']
attendance = np.array([95, 70, 60, 85, 80, 65, 90, 88])
hours      = np.array([ 1,  6,  1,  5,  2,  7,  3,  9])
passed     = np.array([False, True, False, True, False, True, False, True])
for row in zip(names, attendance, hours, passed):
    print('{:6} attendance {:3}%  studies {} h  passed: {}'.format(*row))"""),
    md("## 3 · The teacher’s rule, as a function\nA rule is a recipe a person writes: every number in it (75) was chosen by a person."),
    code("""def on_track(clue, threshold):
    \"\"\"The rule: on track if the clue is at least the threshold, otherwise at risk.\"\"\"
    return clue >= threshold

print(on_track(attendance, 75))""",
         stub="""def on_track(clue, threshold):
    # TODO: return True where clue >= threshold
    raise NotImplementedError

print(on_track(attendance, 75))"""),
    md("## 4 · By hand: count the mistakes\nA mistake is when the rule’s verdict disagrees with what really happened."),
    code("""def mistakes(clue, threshold):
    return int(np.sum(on_track(clue, threshold) != passed))

for n, a, p, ok in zip(names, attendance, passed, on_track(attendance, 75)):
    print(f"{n:6} {a}%  rule says {'on track' if ok else 'at risk ':8}  really {'passed' if p else 'failed'}  {'✓' if ok == p else '✗'}")
print('mistakes:', mistakes(attendance, 75), 'of 8')""",
         stub="""def mistakes(clue, threshold):
    # TODO: count where on_track(...) disagrees with passed
    raise NotImplementedError

print('mistakes:', mistakes(attendance, 75), 'of 8')"""),
    md("Doing nothing (calling everyone “on track”) is the same as a threshold of 0:"),
    code("print('call everyone on track:', mistakes(attendance, 0), 'mistakes')"),
    md("## 5 · Let the machine find the rule\nTry **every** threshold for **every** clue, count the mistakes, keep the best. No person chooses the number."),
    code("""def best_rule(clue, thresholds):
    scores = {t: mistakes(clue, t) for t in thresholds}
    t_best = min(scores, key=scores.get)
    return t_best, scores[t_best], scores

t_att, m_att, att_scores = best_rule(attendance, range(50, 101, 5))
t_hrs, m_hrs, hrs_scores = best_rule(hours, range(0, 11))
print('attendance:', att_scores)
print('hours     :', hrs_scores)
print(f'best attendance rule: at risk below {t_att}% → {m_att} mistakes')
print(f'best hours rule     : at risk below {t_hrs} h → {m_hrs} mistakes')""",
         stub="""def best_rule(clue, thresholds):
    # TODO: score every threshold with mistakes(); return (best threshold, its mistakes, all scores)
    raise NotImplementedError

t_att, m_att, att_scores = best_rule(attendance, range(50, 101, 5))
t_hrs, m_hrs, hrs_scores = best_rule(hours, range(0, 11))"""),
    md("## 6 · PROOF\nThe numbers from the slides, checked by the computer."),
    code("""assert mistakes(attendance, 75) == 5, 'the 75% rule gets 5 of 8 wrong'
assert mistakes(attendance, 0) == 4, 'doing nothing gets only 4 wrong'
assert (t_att, m_att) == (65, 3), 'attendance can do no better than 3 mistakes (at 65%)'
assert (t_hrs, m_hrs) == (4, 0), 'at risk if studying under 4 hours: 0 mistakes'
assert my_prediction_mistakes == mistakes(attendance, 75), 'your prediction matches'
print('✓ proof: 75% rule → 5 · nothing → 4 · best attendance → 3 · under 4 hours → 0')"""),
    md("## 7 · Picture\nEach dot is a student. Hours separate pass and fail with one line; attendance cannot."),
    code("""colors = np.where(passed, 'tab:green', 'tab:red')
plt.scatter(attendance, hours, c=colors, s=120)
for n, a, h in zip(names, attendance, hours):
    plt.annotate(n, (a, h), textcoords='offset points', xytext=(6, 6))
plt.axvline(75, ls='--', color='gray', label='teacher: attendance 75%')
plt.axhline(3.5, color='tab:orange', label='machine: hours 4')
plt.xlabel('attendance %'); plt.ylabel('hours studied per week'); plt.legend(); plt.show()"""),
    md("## 8 · Break it\nThe rule came from only 8 students. Add one who studies 2 hours and still passes: does the best rule survive?"),
    code("""hours2, passed2 = np.append(hours, 2), np.append(passed, True)
print('under 4 h rule now:', int(np.sum((hours2 >= 4) != passed2)), 'mistake(s) → more data, better rules')"""),
    md("## 9 · Your turn\nAsha: attendance 92%, studies 8 hours. What does the teacher’s rule say? What does the learned rule say?"),
    code("print('teacher:', 'on track' if 92 >= 75 else 'at risk', '· learned:', 'on track' if 8 >= 4 else 'at risk')",
         stub="# TODO: apply both rules to Asha (92%, 8 h)"),
    md("## Recap\n- A rule is a recipe a person writes; its numbers are a person’s choice\n- Machine learning tries many rules and keeps the one with the fewest mistakes on past examples\n- The data, not a person, chose “under 4 hours”\n\n**Next (Chapter 3):** you become the model."),
]

# ---------------------------------------------------------------- Chapter 4
NOTEBOOKS["ch04-fit-the-line"] = [
    md("""
# Chapter 4 · Fit the line
**Deck 1 · Live demo.** Write Asha’s rule as code, measure how wrong a rule is, and check every number from the slides.

**You will:** turn a rule in words into a function · compute errors and the loss by hand · prove the slide numbers (33, 0, 80).
"""),
    code(SETUP),
    md("## 1 · Your prediction\nThree classmates: 2, 4, 6 hours of study a week → 50, 60, 70 marks. Asha studies **8 hours**. Write your guess and your rule *before* running anything."),
    code('my_prediction = 80          # ← your guess for Asha\nmy_rule = "+5 marks per hour, base 40"   # ← your rule in words', stub='my_prediction = None   # ← your guess for Asha\nmy_rule = ""           # ← your rule in words'),
    md("## 2 · The class"),
    code("hours = np.array([2, 4, 6])\nmarks = np.array([50, 60, 70])\nfor h, m in zip(hours, marks):\n    print(f'{h} hours → {m} marks')"),
    md("## 3 · The idea\nYour rule *is* a model: **predicted marks = w × hours + b**, where *w* = marks per hour and *b* = base marks.\n\n$$\\hat{y} = w\\,x + b$$"),
    code("def predict(w, b, x):\n    \"\"\"The model: weight × input + bias.\"\"\"\n    return w * x + b\n\nprint('Asha with your rule:', predict(5, 40, 8))",
         stub="def predict(w, b, x):\n    \"\"\"The model: weight × input + bias.\"\"\"\n    # TODO: return w times x plus b\n    raise NotImplementedError\n\nprint('Asha with your rule:', predict(5, 40, 8))"),
    md("## 4 · By hand: how wrong is a bad rule?\nTake a bad first guess, **w = 2, b = 55**. For student A (2 hours, real 50): guess = 2 × 2 + 55 = 59, error = 59 − 50 = **+9**."),
    code("w, b = 2, 55\nguess = predict(w, b, hours)\nerrors = guess - marks\nprint('guesses:', guess)\nprint('errors :', errors)"),
    md("## 5 · The loss: average squared error\nSquare each error (so +9 and −9 can’t cancel, and big misses count more), then average.\n\n$$\\text{loss} = \\frac{1}{n}\\sum (\\hat{y} - y)^2$$"),
    code("def loss(w, b):\n    errors = predict(w, b, hours) - marks\n    return np.mean(errors ** 2)\n\nprint('squares:', (predict(2, 55, hours) - marks) ** 2)\nprint('loss for w=2, b=55:', loss(2, 55))",
         stub="def loss(w, b):\n    # TODO: errors = predictions − real marks; return the mean of the squared errors\n    raise NotImplementedError\n\nprint('loss for w=2, b=55:', loss(2, 55))"),
    md("## 5b · Unroll the sigma\nThe book notation $L = \\frac{1}{n}\\sum_{i=1}^{n} (\\hat{y}_i - y_i)^2$ is just one term per student, then add, then divide by n."),
    code("""guess = predict(2, 55, hours)
terms = [(guess[i] - marks[i]) ** 2 for i in range(3)]   # i = 1, 2, 3 in the slides
print('terms :', terms, '→ Σ =', sum(terms), '→ L = Σ / n =', sum(terms) / len(terms))"""),
    md("## 5c · Hot or cold\nKeep b = 40 and learn w from the loss alone, the way the volunteer did. Note: w = 4 and w = 6 give the same loss."),
    code("""for w_try in [0, 2, 8, 4, 6, 5]:
    print(f'w = {w_try}: loss {loss(w_try, 40):6.1f}')"""),
    md("## 6 · PROOF\nThe same numbers as the slides, checked by the computer."),
    code("""assert list(predict(2, 55, hours) - marks) == [9, 3, -3], 'errors for the bad rule'
assert loss(2, 55) == 33, 'the slide says the bad rule has loss 33'
assert loss(5, 40) == 0, 'your rule fits every student exactly'
assert predict(5, 40, 8) == 80, 'Asha gets 80'
assert my_prediction == predict(5, 40, 8), 'your prediction matches the model'
assert round(loss(4, 40), 1) == round(loss(6, 40), 1) == 18.7, 'hot or cold: w = 4 and 6 tie'
print('✓ proof: 33 · 0 · 80, and your prediction agrees')"""),
    md("## 7 · Picture"),
    code("""xs = np.linspace(0, 10, 50)
plt.scatter(hours, marks, s=80, label='classmates', zorder=3)
plt.plot(xs, predict(2, 55, xs), '--', label='bad rule: 2x + 55 (loss 33)')
plt.plot(xs, predict(5, 40, xs), label='your rule: 5x + 40 (loss 0)')
plt.scatter([8], [predict(5, 40, 8)], s=120, marker='*', label='Asha → 80', zorder=4)
plt.xlabel('hours studied per week'); plt.ylabel('marks'); plt.legend(); plt.show()"""),
    md("## 8 · Break it\nWhat happens to the loss if you **don’t square** the errors? Try the plain average for the bad rule."),
    code("print('plain average of errors:', np.mean(predict(2, 55, hours) - marks))\nprint('→ positive and negative errors partly cancel; that is why we square')"),
    md("## 9 · Your turn\nFind another (w, b) with a **loss under 10**. How close to 5 and 40 must you be?"),
    code("# try your own values\nprint(loss(4.5, 43))", stub="# TODO: try your own w and b\n# print(loss(?, ?))"),
    md("## Recap\n- A rule in words = a model: ŷ = w·x + b\n- Error = guess − real; loss = average squared error\n- The perfect rule for the class: w = 5, b = 40 → loss 0 → Asha 80\n\n**Next (Chapter 8):** how a machine finds w and b by itself."),
]

# ---------------------------------------------------------------- Chapter 6
NOTEBOOKS["ch06-next-word"] = [
    md("""
# Chapter 6 · A tiny language model
**Deck 1 · Live demo.** Build the smallest possible generative AI: count which word comes next, predict, and write a sentence one word at a time.

**You will:** count next words · turn counts into percentages · prove the slide numbers (50%, 75%, 100%) · generate text.
"""),
    code("from collections import Counter"),
    md("## 1 · Your prediction\nFinish the sentence: **“Ravi passed the …”**. Which word, and how sure are you?"),
    code("my_prediction = 'exam'   # ← your word", stub="my_prediction = None   # ← your word"),
    md("## 2 · What the machine has read"),
    code("""sentences = [
    'asha studied hard and passed the exam',
    'ravi passed the exam',
    'meena passed the test',
    'kiran revised the notes and passed the exam',
    'leela failed the quiz',
]
for s in sentences:
    print(s.split())"""),
    md("## 3 · Count what follows a context\nSlide along every sentence; whenever the words match the context, note the next word."),
    code("""def next_words(context):
    ctx = context.split()
    counts = Counter()
    for s in sentences:
        w = s.split()
        for i in range(len(w) - len(ctx)):
            if w[i:i + len(ctx)] == ctx:
                counts[w[i + len(ctx)]] += 1
    return counts

print('after "the":       ', next_words('the'))
print('after "passed the":', next_words('passed the'))""",
         stub="""def next_words(context):
    ctx = context.split()
    counts = Counter()
    # TODO: for every sentence and every position, if the words match ctx, count the word that follows
    return counts

print(next_words('the'))"""),
    md("## 4 · Counts → how sure\n$$P(\\text{word} \\mid \\text{context}) = \\frac{\\text{times the word followed the context}}{\\text{times the context appeared}}$$"),
    code("""def predict(context):
    counts = next_words(context)
    word, n = counts.most_common(1)[0]
    return word, n / sum(counts.values())

for ctx in ['the', 'passed the', 'failed the']:
    word, p = predict(ctx)
    print(f'{ctx!r:14} → {word!r:8} {p:.0%} sure')""",
         stub="""def predict(context):
    # TODO: the most common next word and its share of all counts
    raise NotImplementedError"""),
    md("## 5 · PROOF\nThe numbers from the slides."),
    code("""assert next_words('the') == Counter(exam=3, test=1, notes=1, quiz=1)
assert predict('the') == ('exam', 0.5), '“the” alone: 3 of 6 = 50%'
assert predict('passed the') == ('exam', 0.75), '“passed the”: 3 of 4 = 75%'
assert predict('failed the') == ('quiz', 1.0), 'one example → 100%: overconfident'
assert my_prediction == predict('passed the')[0], 'you and the machine agree'
print('✓ proof: the → exam 50% · passed the → exam 75% · failed the → quiz 100%')"""),
    md("## 6 · Generate: predict, append, repeat\nUse the last two words as context (fall back to one word if two were never seen)."),
    code("""def generate(start, max_words=8):
    words = start.split()
    for _ in range(max_words):
        for k in (2, 1):
            ctx = ' '.join(words[-k:])
            if next_words(ctx):
                words.append(predict(ctx)[0])
                break
        else:
            break   # nothing ever followed: end of sentence
    return ' '.join(words)

print(generate('ravi'))
print(generate('leela'))""",
         stub="""def generate(start, max_words=8):
    words = start.split()
    # TODO: repeat: predict the next word from the last words, append it; stop when nothing follows
    return ' '.join(words)

print(generate('ravi'))"""),
    code("assert generate('ravi') == 'ravi passed the exam'\nprint('✓ ravi → passed → the → exam')"),
    md("## 7 · Picture"),
    code("""import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
for ax, ctx in zip(axes, ['the', 'passed the']):
    c = next_words(ctx); total = sum(c.values())
    ax.barh(list(c), [v / total for v in c.values()], color='tab:green')
    ax.set_title(f'after “{ctx}”'); ax.set_xlim(0, 1); ax.invert_yaxis()
plt.tight_layout(); plt.show()"""),
    md("## 8 · Break it\nAdd ten sentences that end in “test”. What does the model predict after “passed the” now?"),
    code("""saved = list(sentences)
sentences += ['someone passed the test'] * 10
print(predict('passed the'))
sentences = saved   # restore""",
         stub="# TODO: add sentences, predict again, then restore"),
    md("## 9 · Your turn\nAdd your own sentences about the class. Generate from a name you added."),
    code("# TODO", stub="# TODO"),
    md("## Recap\n- Generative AI predicts the next word, then repeats\n- More context → surer predictions; one example → overconfident\n- Real chat assistants use billions of sentences and a neural network instead of a simple count; the idea is the same\n\n**Next (Chapter 8):** how a machine learns its numbers by itself."),
]

# ---------------------------------------------------------------- Chapter 10
NOTEBOOKS["ch10-gradient-descent"] = [
    md("""
# Chapter 10 · Gradient descent by hand
**Deck 2 · Live demo.** The machine starts at w = 0, b = 0 and finds the rule on its own, one step at a time.

**You will:** compute one step by hand · loop it in NumPy · watch w overshoot and come back · prove it ends at w = 5, b = 40.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nHow many steps will gradient descent need (with step size 0.01) until Asha’s prediction is within half a mark of 80?"),
    code("my_prediction_steps = 1600   # ← your guess", stub="my_prediction_steps = None   # ← your guess"),
    code("hours = np.array([2., 4., 6.])\nmarks = np.array([50., 60., 70.])\n\ndef loss(w, b):\n    return np.mean((w * hours + b - marks) ** 2)"),
    md("## 2 · The slopes\nOne slope per knob (Chapter 9):\n\n$$\\frac{\\partial L}{\\partial w} = \\frac{2}{n}\\sum(\\hat{y}-y)\\,x \\qquad \\frac{\\partial L}{\\partial b} = \\frac{2}{n}\\sum(\\hat{y}-y)$$"),
    code("def slopes(w, b):\n    errors = w * hours + b - marks\n    return 2 * np.mean(errors * hours), 2 * np.mean(errors)\n\nprint('slopes at w=0, b=0:', slopes(0, 0))",
         stub="def slopes(w, b):\n    errors = w * hours + b - marks\n    # TODO: return (2 × mean(errors × hours), 2 × mean(errors))\n    raise NotImplementedError\n\nprint('slopes at w=0, b=0:', slopes(0, 0))"),
    md("## 3 · One step by hand\n$$w \\leftarrow w - \\eta \\cdot \\frac{\\partial L}{\\partial w}$$ with step size η = 0.01."),
    code("eta = 0.01\ngw, gb = slopes(0, 0)\nw1, b1 = 0 - eta * gw, 0 - eta * gb\nprint(f'step 1: w = {w1:.2f}, b = {b1:.2f}, loss {loss(0, 0):,.1f} → {loss(w1, b1):,.1f}')",
         stub="eta = 0.01\ngw, gb = slopes(0, 0)\n# TODO: one step: w1 = 0 − eta × gw ; b1 = 0 − eta × gb\nw1, b1 = None, None\nprint(w1, b1)"),
    md("## 4 · The loop"),
    code("""def descend(eta, steps, w=0.0, b=0.0):
    history = [(w, b, loss(w, b))]
    for _ in range(steps):
        gw, gb = slopes(w, b)
        w, b = w - eta * gw, b - eta * gb
        history.append((w, b, loss(w, b)))
    return np.array(history)

h = descend(0.01, 3000)
w_end, b_end = h[-1, 0], h[-1, 1]
print(f'after 3,000 steps: w = {w_end:.3f}, b = {b_end:.3f}, Asha → {8 * w_end + b_end:.2f}')""",
         stub="""def descend(eta, steps, w=0.0, b=0.0):
    history = [(w, b, loss(w, b))]
    for _ in range(steps):
        # TODO: compute the slopes, take one step, append (w, b, loss)
        pass
    return np.array(history)

h = descend(0.01, 3000)"""),
    code("""def steps_to_asha(eta, limit=100_000):
    w = b = 0.0
    for i in range(1, limit):
        gw, gb = slopes(w, b)
        w, b = w - eta * gw, b - eta * gb
        if not np.isfinite(w) or abs(w) > 1e9:
            return None
        if abs(8 * w + b - 80) < 0.5 and abs(w - 5) < 0.1 and abs(b - 40) < 0.5:
            return i
steps = steps_to_asha(0.01)
print('steps to reach Asha ≈ 80:', steps, '· your guess:', my_prediction_steps)"""),
    md("## 5 · PROOF"),
    code("""assert np.allclose(slopes(0, 0), (-506.6667, -120.0), atol=1e-3), 'slopes −506.7 and −120'
assert round(w1, 2) == 5.07 and round(b1, 2) == 1.20, 'step 1: w = 5.07, b = 1.20'
assert round(loss(0, 0), 1) == 3666.7 and round(loss(w1, b1), 1) == 1484.8, 'loss 3,666.7 → 1,484.8'
assert h[:20, 0].max() > 12, 'w overshoots past 12'
assert abs(w_end - 5) < 0.01 and abs(b_end - 40) < 0.05, 'ends at w = 5, b = 40'
assert steps == 1604, 'the slide: about 1,604 steps'
print('✓ proof: every slide number reproduced')"""),
    md("## 6 · Picture: fast at first, then slow; w overshoots"),
    code("""fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].semilogy(h[:, 2]); ax[0].set_title('loss (log scale)'); ax[0].set_xlabel('step')
ax[1].plot(h[:, 0], label='w'); ax[1].plot(h[:, 1], label='b'); ax[1].axhline(5, ls=':'); ax[1].axhline(40, ls=':')
ax[1].set_title('w races ahead and overshoots; b crawls up to 40'); ax[1].set_xlabel('step'); ax[1].legend()
plt.show()"""),
    md("## 7 · Break it\nFlip the minus sign to a plus: step *up* the slope. What happens?"),
    code("w = b = 0.0\nfor i in range(5):\n    gw, gb = slopes(w, b)\n    w, b = w + 0.01 * gw, b + 0.01 * gb   # wrong way!\n    print(f'step {i + 1}: loss {loss(w, b):,.0f}')"),
    md("## 8 · Your turn\nStart from **w = 10, b = 100**. Does it still end at 5 and 40?"),
    code("h2 = descend(0.01, 3000, w=10, b=100)\nprint(h2[-1])", stub="# TODO: descend from w=10, b=100 and print the last row"),
    md("## Recap\n- Slopes: 2/n · Σ error × hours (w) and 2/n · Σ error (b)\n- Update: w ← w − η × slope, repeated\n- Step 1: 5.07, 1.20 · after ~1,600 steps: Asha ≈ 80 · ends at w = 5, b = 40"),
]

# ---------------------------------------------------------------- Chapter 11
NOTEBOOKS["ch11-step-size"] = [
    md("""
# Chapter 11 · How big a step?
**Deck 2 · Live demo.** Race four step sizes and find where learning breaks.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nWhich is the smallest of these step sizes that **explodes**: 0.001, 0.01, 0.04, 0.055?"),
    code("my_prediction = 0.055", stub="my_prediction = None"),
    code("""hours = np.array([2., 4., 6.]); marks = np.array([50., 60., 70.])
loss = lambda w, b: np.mean((w * hours + b - marks) ** 2)
def slopes(w, b):
    e = w * hours + b - marks
    return 2 * np.mean(e * hours), 2 * np.mean(e)

def run(eta, steps):
    w = b = 0.0; losses = [loss(w, b)]
    for _ in range(steps):
        gw, gb = slopes(w, b); w, b = w - eta * gw, b - eta * gb
        losses.append(loss(w, b))
        if not np.isfinite(losses[-1]) or losses[-1] > 1e12:
            break
    return np.array(losses)"""),
    md("## 2 · The race"),
    code("""for eta in [0.001, 0.01, 0.04, 0.055]:
    L = run(eta, 500)
    plt.semilogy(L, label=f'eta {eta}')
plt.ylim(1e-4, 1e8); plt.xlabel('step'); plt.ylabel('loss (log)'); plt.legend(); plt.show()"""),
    md("## 3 · Steps to reach Asha ≈ 80"),
    code("""def steps_to_asha(eta, limit=100_000):
    w = b = 0.0
    for i in range(1, limit):
        gw, gb = slopes(w, b); w, b = w - eta * gw, b - eta * gb
        if not np.isfinite(w) or abs(w) > 1e9:
            return 'explodes'
        if abs(8 * w + b - 80) < 0.5 and abs(w - 5) < 0.1 and abs(b - 40) < 0.5:
            return i
table = {eta: steps_to_asha(eta) for eta in [0.001, 0.01, 0.04, 0.055]}
for eta, s in table.items():
    print(f'eta {eta:<6} → {s}')"""),
    md("## 4 · Find the cliff\nBisection: keep halving the gap between a step size that works and one that explodes."),
    code("""def explodes(eta):
    return isinstance(steps_to_asha(eta, 20_000), str)

lo, hi = 0.04, 0.055
for _ in range(20):
    mid = (lo + hi) / 2
    lo, hi = (lo, mid) if explodes(mid) else (mid, hi)
cliff = (lo + hi) / 2
print(f'the cliff is near eta = {cliff:.4f}')""",
         stub="""def explodes(eta):
    return isinstance(steps_to_asha(eta, 20_000), str)

lo, hi = 0.04, 0.055
# TODO: repeat 20 times: try the middle; if it explodes, it becomes the new hi, else the new lo
cliff = None"""),
    md("## 5 · PROOF"),
    code("""assert table == {0.001: 16057, 0.01: 1604, 0.04: 400, 0.055: 'explodes'}, 'the slide table'
assert abs(cliff - 0.0512) < 0.0005, 'the safe limit is about 0.051'
assert my_prediction == 0.055
print('✓ proof: the race table and the cliff match the slides')"""),
    md("## 6 · Your turn\nTry 0.05 and 0.052. Which side of the cliff is each?"),
    code("print(steps_to_asha(0.05), steps_to_asha(0.052))", stub="# TODO"),
    md("## Recap\nToo small crawls (~16,000 steps), 0.04 is fast (~400), and just past ~0.051 every step overshoots and the loss explodes."),
]

# ---------------------------------------------------------------- Chapter 12
NOTEBOOKS["ch12-mini-batch"] = [
    md("""
# Chapter 12 · Whole school, mini-batch, one student
**Deck 2 · Live demo.** Train on 1,000 students three ways with the **same amount of work**, and see why every modern model uses mini-batches.

**You will:** build a noisy school · find the best possible line · write one training function for any batch size · prove the slide table.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nEach method may look at 50,000 students in total (η = 0.01). Whole school: 50 steps. Mini-batch of 32: 1,563 steps. One student: 50,000 steps. Which ends closest to w = 5, b = 40?"),
    code("my_prediction = 32   # ← batch size you think wins: 1000, 32 or 1", stub="my_prediction = None   # ← 1000, 32 or 1"),
    md("## 2 · The school\nSame rule as our class (5 marks per hour + 40), but each real mark wobbles up to ±5. The numbers are generated by a fixed recipe, so the slides and this notebook see exactly the same students."),
    code("""N = 1000
i = np.arange(N)
hours = 1 + (i * 3) % 10                  # 1 … 10 hours
wobble = (i * 37) % 11 - 5                # −5 … +5 marks
marks = 5 * hours + 40 + wobble
order = (i * 7919) % N                    # a fixed shuffled order to visit students
print(hours[:10], marks[:10])"""),
    md("## 3 · The best any line can do\nBecause of the wobble no line hits every student. Least squares finds the best line directly; its loss is the floor."),
    code("""def loss(w, b):
    return np.mean((w * hours + b - marks) ** 2)

best_w, best_b = np.polyfit(hours, marks, 1)
print(f'best line: w = {best_w:.3f}, b = {best_b:.3f}, loss = {loss(best_w, best_b):.2f}')"""),
    md("## 3b · Is a sample enough?\nThe slope for w at the start (w = 0, b = 0), from all 1,000 students vs from groups of 32."),
    code("""def start_slope(idx):
    return 2 * np.mean((0 * hours[idx] + 0 - marks[idx]) * hours[idx])

all_students = start_slope(np.arange(N))
batches = [start_slope(order[k * 32:(k + 1) * 32]) for k in range(3)]
print(f'all 1,000 students: {all_students:.1f}')
print('three groups of 32:', [round(v, 1) for v in batches])
assert round(all_students, 1) == -825.0 and [round(v, 1) for v in batches] == [-819.8, -795.1, -849.1]
print('✓ 32 students give nearly the same slope, for 31× less work')"""),
    md("## 4 · One training function, any batch size\nThe update rule from Chapter 10, but each step only looks at `batch_size` students, taken in turn from the shuffled order.\n\n$$w \\leftarrow w - \\eta \\cdot \\frac{2}{B}\\sum_{\\text{batch}} (\\hat{y}-y)\\,x \\qquad b \\leftarrow b - \\eta \\cdot \\frac{2}{B}\\sum_{\\text{batch}} (\\hat{y}-y)$$"),
    code("""def train(batch_size, budget=50_000, eta=0.01):
    w = b = 0.0
    seen = pos = steps = 0
    curve = [(0, loss(w, b))]
    while seen < budget:
        idx = order[(pos + np.arange(batch_size)) % N]
        pos = (pos + batch_size) % N
        err = w * hours[idx] + b - marks[idx]
        w -= eta * 2 * np.mean(err * hours[idx])
        b -= eta * 2 * np.mean(err)
        seen += batch_size
        steps += 1
        curve.append((seen, loss(w, b)))
    return steps, w, b, loss(w, b), np.array(curve)

NAMES = {1000: 'Whole school (1,000)', 32: 'Mini-batch (32)', 1: 'One student (1)'}
results = {bs: train(bs) for bs in (1000, 32, 1)}
for bs, (steps, w, b, L, _) in results.items():
    print(f'{NAMES[bs]:<22} {steps:>6,} steps → w {w:.2f}, b {b:.2f}, loss {L:.1f}')""",
         stub="""def train(batch_size, budget=50_000, eta=0.01):
    w = b = 0.0
    seen = pos = steps = 0
    curve = [(0, loss(w, b))]
    while seen < budget:
        idx = order[(pos + np.arange(batch_size)) % N]
        pos = (pos + batch_size) % N
        # TODO: errors for this batch, then update w and b with the mean slopes
        seen += batch_size
        steps += 1
        curve.append((seen, loss(w, b)))
    return steps, w, b, loss(w, b), np.array(curve)

results = {bs: train(bs) for bs in (1000, 32, 1)}"""),
    md("## 5 · PROOF\nThe table on the slide."),
    code("""r = {bs: tuple(round(v, 2) for v in res[1:4]) + (res[0],) for bs, res in results.items()}
assert r[1000] == (9.48, 8.82, 218.46, 50), r[1000]
assert r[32] == (5.03, 39.95, 10.02, 1563), r[32]
assert r[1] == (5.49, 39.94, 18.81, 50000), r[1]
assert round(loss(best_w, best_b), 2) == 10.01
assert my_prediction == 32, 'the mini-batch wins'
print('✓ proof: whole school 218.5 · mini-batch 10.0 (best possible 10.0) · one student 18.8')"""),
    md("## 6 · Picture"),
    code("""for bs, color in [(1000, 'tab:blue'), (32, 'tab:green'), (1, 'tab:red')]:
    c = results[bs][4]
    plt.plot(c[:, 0], np.minimum(c[:, 1], 300), color=color, label=NAMES[bs])
plt.axhline(loss(best_w, best_b), ls='--', color='gray', label='best possible ≈ 10')
plt.xlabel('students looked at (work done)'); plt.ylabel('loss (capped at 300)'); plt.legend(); plt.show()"""),
    md("## 7 · Break it\nGive the whole school 100× more work. Does it catch up?"),
    code("steps, w, b, L, _ = train(1000, budget=5_000_000)\nprint(f'{steps:,} steps → w {w:.2f}, b {b:.2f}, loss {L:.2f}  (it gets there, at 100× the cost)')"),
    md("## 8 · Your turn\nTry batch sizes 8 and 128 with the same 50,000 budget. Where is the sweet spot?"),
    code("for bs in (8, 32, 128):\n    print(bs, [round(v, 2) for v in train(bs)[1:4]])", stub="# TODO: try batch sizes 8 and 128"),
    md("## Recap\n- Whole school per step: exact slope, but very few steps for the work\n- One student per step: many steps, but jumpy: never settles\n- Mini-batch: the best of both, and the standard way to train every modern model\n- One pass over all students = one epoch; 50,000 looks = 50 epochs\n\n**Next (Chapter 13):** more clues than hours."),
]

# ---------------------------------------------------------------- Chapter 13
NOTEBOOKS["ch13-two-clues"] = [
    md("""
# Chapter 13 · Two clues at once
**Deck 3 · Live demo.** Learn w₁ (per hour), w₂ (per practice test) and b from four students, then predict Asha.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nE: 2 h, 1 test → 46 · F: 4 h, 1 test → 56 · G: 2 h, 3 tests → 54 · H: 4 h, 3 tests → 64. **Asha: 8 hours, 2 tests?**"),
    code("my_prediction = 80", stub="my_prediction = None"),
    code("X = np.array([[2, 1], [4, 1], [2, 3], [4, 3]], dtype=float)   # columns: hours, tests\ny = np.array([46, 56, 54, 64], dtype=float)\nasha = np.array([8, 2], dtype=float)"),
    md("## 2 · The model\n$$\\hat{y} = w_1 x_1 + w_2 x_2 + b = \\mathbf{w}\\cdot\\mathbf{x} + b$$ A weighted sum is a receipt: clues are quantities, weights are prices. `X @ w` does every student at once."),
    md("## 3 · Gradient descent with three knobs\nOne slope per knob: errors × hours for w₁, errors × tests for w₂, errors alone for b."),
    code("""w = np.zeros(2); b = 0.0; eta = 0.04
for step in range(10_000):
    errors = X @ w + b - y
    w -= eta * 2 * X.T @ errors / len(y)
    b -= eta * 2 * errors.mean()
print('w1, w2 =', w.round(3), ' b =', round(b, 3))
print('Asha →', round(asha @ w + b, 2))""",
         stub="""w = np.zeros(2); b = 0.0; eta = 0.04
for step in range(10_000):
    errors = X @ w + b - y
    # TODO: w -= eta × 2 × Xᵀ·errors / n ;  b -= eta × 2 × mean(errors)
    pass
print(w, b)"""),
    md("## 4 · PROOF"),
    code("""assert np.allclose(w, [5, 4], atol=1e-3) and abs(b - 32) < 1e-3, 'w1 = 5, w2 = 4, b = 32'
assert np.allclose(X @ [5, 4] + 32, y), 'the rule reproduces every student'
assert round(asha @ w + b, 2) == 80 == my_prediction, 'Asha → 80'
print('✓ proof: 5, 4, 32 → Asha 80')"""),
    md("## 5 · The same answer from scikit-learn"),
    code("from sklearn.linear_model import LinearRegression\nm = LinearRegression().fit(X, y)\nprint('sklearn:', m.coef_.round(3), round(m.intercept_, 3), '→ Asha', m.predict([asha]).round(2))"),
    md("## 6 · Your turn\nAdd a fifth student who breaks the rule (e.g. 6 h, 2 tests → 50). Re-run: what happens to the loss and the weights?"),
    code("# TODO: add a row to X and y and re-run the loop", stub="# TODO"),
    md("## Recap\nMore clues = more weights. The learning loop is unchanged: one slope per knob."),
]

# ---------------------------------------------------------------- Chapter 14
NOTEBOOKS["ch14-curves"] = [
    md("""
# Chapter 14 · When the pattern curves
**Deck 3 · Live demo.** A straight line can’t fit the sleep hump; one extra clue, sleep², bends it.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nSleep 4, 6, 8, 10, 12 hours → 55, 70, 75, 70, 55 marks. **Marks for 7 hours of sleep?**"),
    code("my_prediction = 74", stub="my_prediction = None"),
    code("sleep = np.array([4, 6, 8, 10, 12], dtype=float)\nmarks = np.array([55, 70, 75, 70, 55], dtype=float)"),
    md("## 2 · The best straight line\nLeast squares (the exact answer gradient descent would reach)."),
    code("""A_line = np.c_[sleep, np.ones_like(sleep)]
slope, base = np.linalg.lstsq(A_line, marks, rcond=None)[0]
line = slope * sleep + base
line_loss = np.mean((line - marks) ** 2)
print(f'best line: slope {slope:.3f}, base {base:.1f}, loss {line_loss:.1f}')"""),
    md("## 2b · How did we know? Subtract neighbours twice\nSleep goes up in equal steps of 2. Constant 1st differences mean a line; constant 2nd differences mean a square curve."),
    code("""marks_by_sleep = np.array([55, 70, 75, 70, 55])
d1 = np.diff(marks_by_sleep)
d2 = np.diff(d1)
print('1st differences:', d1, '→ not constant: not a line')
print('2nd differences:', d2, '→ constant: add sleep²; negative: bends down')
assert list(d1) == [15, 5, -5, -15] and list(d2) == [-10, -10, -10]
print('✓ the data asks for sleep² (and deck 1: hours 2, 4, 6 → 50, 60, 70 gives', np.diff([50, 60, 70]), ': a line)')"""),
    md("## 3 · Add sleep² as a clue\n$$\\hat{y} = w_1\\,\\text{sleep} + w_2\\,\\text{sleep}^2 + b$$ Still a weighted sum, just one more column."),
    code("""A_curve = np.c_[sleep, sleep ** 2, np.ones_like(sleep)]
w1, w2, b = np.linalg.lstsq(A_curve, marks, rcond=None)[0]
curve = lambda s: w1 * s + w2 * s ** 2 + b
curve_loss = np.mean((curve(sleep) - marks) ** 2)
print(f'curve: w1 = {w1:.2f}, w2 = {w2:.2f}, b = {b:.2f}, loss {curve_loss:.6f}')
print('7 hours →', round(curve(7), 2))""",
         stub="""A_curve = None   # TODO: columns sleep, sleep², 1
# w1, w2, b = np.linalg.lstsq(A_curve, marks, rcond=None)[0]"""),
    md("## 4 · PROOF"),
    code("""assert abs(slope) < 1e-9 and abs(base - 65) < 1e-9 and round(line_loss, 6) == 70, 'flat line at 65, loss 70'
assert np.allclose([w1, w2, b], [20, -1.25, -5]), 'w1 = 20, w2 = −1.25, b = −5'
assert curve_loss < 1e-9 and round(curve(7), 2) == 73.75, 'loss 0 and 73.75 at 7 hours'
assert abs(my_prediction - curve(7)) <= 1.5, 'your guess was close'
print('✓ proof: line 65 / loss 70 · curve 73.75 / loss 0')"""),
    md("## 5 · Picture"),
    code("""xs = np.linspace(3, 13, 100)
plt.scatter(sleep, marks, s=80, zorder=3, label='students')
plt.plot(xs, slope * xs + base, '--', label='best line (flat at 65)')
plt.plot(xs, curve(xs), label='with sleep² (curve)')
plt.scatter([7], [curve(7)], marker='*', s=150, zorder=4, label='Asha, 7 h → 73.75')
plt.xlabel('sleep per night (hours)'); plt.ylabel('marks'); plt.legend(); plt.show()"""),
    md("## 6 · Your turn\nAdd sleep³ as a fourth column. Does it help on these five students, or just add risk?"),
    code("# TODO", stub="# TODO"),
    md("## Recap\nA line can’t bend. Give the model a curved clue (sleep²) and the same method fits the hump. Neural networks will learn such clues by themselves."),
]

# ---------------------------------------------------------------- Chapter 15 / 16
NOTEBOOKS["ch15-pass-fail"] = [
    md("""
# Chapters 15–16 · Pass or fail
**Deck 3 · Live demo.** Learn P(pass) from hours with the sigmoid, log loss and gradient descent.
"""),
    code(SETUP),
    md("## 1 · Your prediction\n1, 2, 3 hours → failed · 6, 7, 8 hours → passed. **Asha (8 h)? Neha (4.5 h)?**"),
    code('my_prediction = {"Asha": "pass", "Neha": "50/50"}', stub='my_prediction = {"Asha": None, "Neha": None}'),
    code("hours = np.array([1, 2, 3, 6, 7, 8], dtype=float)\npassed = np.array([0, 0, 0, 1, 1, 1], dtype=float)\nsigmoid = lambda z: 1 / (1 + np.exp(-z))"),
    md("## 2 · By hand with w = 1.5, b = −6.75\n$$P(\\text{pass}) = \\sigma(w\\cdot\\text{hours} + b) = \\frac{1}{1 + e^{-z}}$$"),
    code("for h in [8, 4.5]:\n    z = 1.5 * h - 6.75\n    print(f'{h} h: z = {z:.2f} → P(pass) = {sigmoid(z):.3f}')"),
    md("## 3 · Log loss: −log(probability given to what happened)"),
    code("for p in [0.995, 0.5, 0.02]:\n    print(f'p = {p}: cost {-np.log(p):.3f}')"),
    md("## 4 · Gradient descent\nThe slope has the same shape as for marks: (p − y) × hours."),
    code("""w = b = 0.0
for step in range(5000):
    p = sigmoid(w * hours + b)
    w -= 0.1 * np.mean((p - passed) * hours)
    b -= 0.1 * np.mean(p - passed)
boundary = -b / w
print(f'learned w = {w:.2f}, b = {b:.2f} · 50% point at {boundary:.2f} hours')
print(f'Asha P(pass) = {sigmoid(8 * w + b):.3f} · Neha = {sigmoid(4.5 * w + b):.2f}')""",
         stub="""w = b = 0.0
for step in range(5000):
    p = sigmoid(w * hours + b)
    # TODO: w -= 0.1 × mean((p − passed) × hours) ; b -= 0.1 × mean(p − passed)
    pass"""),
    md("## 5 · PROOF"),
    code("""assert round(sigmoid(1.5 * 8 - 6.75), 3) == 0.995 and sigmoid(0) == 0.5, 'Asha 0.995 · Neha 0.5 (slides)'
assert [round(-np.log(p), 3) for p in (0.995, 0.9, 0.5, 0.1, 0.02)] == [0.005, 0.105, 0.693, 2.303, 3.912], 'log-loss table'
assert round(np.log(0.02) / np.log(0.995)) == 780, 'sure and wrong costs about 780× more'
assert 3 < boundary < 6, 'the learned 50% point sits in the gap'
assert sigmoid(8 * w + b) > 0.99, 'Asha almost surely passes'
print('✓ proof: slide numbers reproduced; boundary', round(boundary, 2), 'hours')"""),
    md("## 6 · Picture"),
    code("""xs = np.linspace(0, 10, 200)
plt.scatter(hours, passed, s=80, zorder=3)
plt.plot(xs, sigmoid(w * xs + b), label='learned S-curve')
plt.axhline(0.5, ls=':'); plt.axvline(boundary, ls=':')
plt.xlabel('hours'); plt.ylabel('P(pass)'); plt.legend(); plt.show()"""),
    md("## 7 · Your turn\nAdd a student who studied 7 hours and **failed**. Re-train. What happens to the 50% point?"),
    code("# TODO", stub="# TODO"),
    md("## Recap\nSigmoid squeezes the weighted sum into a probability; log loss punishes confident mistakes; the slope is (p − y) × clue."),
]

# ---------------------------------------------------------------- Chapter 17
NOTEBOOKS["ch17-rare-cases"] = [
    md("""
# Chapter 17 · When “yes” is rare
**Deck 3 · Live demo.** Judge a dropout model properly: four boxes, recall and precision.
"""),
    code(SETUP),
    md("## 1 · Your prediction\n100 students, 3 drop out. A model that **never** flags anyone: what accuracy? How many dropouts does it catch?"),
    code("my_prediction = {'accuracy': 0.97, 'caught': 0}", stub="my_prediction = {'accuracy': None, 'caught': None}"),
    md("## 2 · The 100 students\nEach has a risk score from a model (the same scores as the slide calculator)."),
    code("""drop = np.array([0.9, 0.7, 0.3])                                   # 3 dropouts
stay = np.r_[[0.8, 0.65, 0.55], 0.02 + 0.43 * np.arange(94) / 93]   # 97 who stay
scores = np.r_[drop, stay]
truth = np.r_[np.ones(3), np.zeros(97)]                            # 1 = dropped out
print(len(scores), 'students ·', int(truth.sum()), 'dropouts')"""),
    md("## 3 · Four boxes"),
    code("""def boxes(threshold):
    flag = scores >= threshold
    tp = int(np.sum(flag & (truth == 1))); fp = int(np.sum(flag & (truth == 0)))
    fn = int(np.sum(~flag & (truth == 1))); tn = int(np.sum(~flag & (truth == 0)))
    return tp, fp, fn, tn

tp, fp, fn, tn = boxes(0.5)
print(f'caught {tp} · false alarms {fp} · missed {fn} · correctly left alone {tn}')""",
         stub="""def boxes(threshold):
    flag = scores >= threshold
    # TODO: count tp (flagged & dropout), fp (flagged & stayed), fn, tn
    raise NotImplementedError"""),
    md("## 4 · Scores"),
    code("""accuracy = (tp + tn) / 100
recall = tp / (tp + fn)
precision = tp / (tp + fp)
lazy_accuracy = 97 / 100
print(f'accuracy {accuracy:.0%} (lazy {lazy_accuracy:.0%}) · recall {recall:.0%} · precision {precision:.0%}')"""),
    md("## 5 · PROOF"),
    code("""assert (tp, fp, fn, tn) == (2, 3, 1, 94), 'the four boxes on the slide'
assert accuracy == 0.96 < lazy_accuracy == 0.97, 'the model is LESS accurate than doing nothing…'
assert tp == 2 and my_prediction['caught'] == 0, '…yet it catches 2 of 3 dropouts'
assert round(recall, 2) == 0.67 and precision == 0.4, 'recall 67% · precision 40%'
assert boxes(0.25)[:3] == (3, 47, 0), 'threshold 0.25: all caught, 50 calls'
print('✓ proof: 96% < 97%, yet 2 of 3 caught · recall 67% · precision 40%')"""),
    md("## 6 · Sweep the threshold"),
    code("""ts = np.round(np.arange(0.05, 0.96, 0.05), 2)
rec = [boxes(t)[0] / 3 for t in ts]
prec = [boxes(t)[0] / max(1, boxes(t)[0] + boxes(t)[1]) for t in ts]
plt.plot(ts, rec, 'o-', label='recall (dropouts caught)')
plt.plot(ts, prec, 's-', label='precision (calls needed)')
plt.xlabel('threshold'); plt.legend(); plt.show()"""),
    md("## 6b · The trade-off table (as on the slide)"),
    code("""print(f"{'risk ≥':>7} {'calls':>6} {'caught':>7} {'missed':>7} {'accuracy':>9} {'recall':>7} {'precision':>10}")
rows = {}
for t in (0.3, 0.5, 0.75, 0.85):
    tp, fp, fn, tn = boxes(t)
    rows[t] = (tp + fp, tp, fn, tp + tn, round(100 * tp / 3), round(100 * tp / (tp + fp)))
    print(f'{t:>7} {tp + fp:>6} {tp:>7} {fn:>7} {tp + tn:>8}% {rows[t][4]:>6}% {rows[t][5]:>9}%')
assert rows[0.3] == (39, 3, 0, 64, 100, 8) and rows[0.5] == (5, 2, 1, 96, 67, 40)
assert rows[0.75] == (2, 1, 2, 97, 33, 50) and rows[0.85] == (1, 1, 2, 98, 33, 100)
print('✓ accuracy is highest (98%) when we catch only 1 of 3')"""),
    md("## 7 · Your turn\nPick the threshold you would defend to the head teacher, and explain the trade-off in one sentence."),
    code("# TODO", stub="# TODO"),
    md("## Recap\nWhen “yes” is rare, accuracy lies. Count the four boxes; report recall and precision; choose the threshold by what each mistake costs."),
]

# ================================================================= Deck 4 · neural networks
CLOCK_DATA = """# The body-clock students: x1 = exam time (0 morning, 1 evening), x2 = body clock (0 early bird, 1 night owl)
names = ['Kabir', 'Zara', 'Tara', 'Omar']
X = np.array([[0, 0], [1, 1], [1, 0], [0, 1]], dtype=float)
y = np.array([1, 1, 0, 0], dtype=float)          # pass when exam time matches body clock
for n, (a, b), r in zip(names, X, y):
    print(f"{n:6} exam {'evening' if a else 'morning':8} {'night owl' if b else 'early bird':10} → {'pass' if r else 'fail'}")"""

NOTEBOOKS["ch18-no-straight-line"] = [
    md("""
# Chapter 18 · A pattern no straight line can learn
**Deck 4 · Live demo.** Show that one neuron (one straight cut) can never get all four body-clock students right.

**You will:** type the four students · test one clue at a time · search 15,625 straight lines · prove the best is 3 of 4.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nAsha: early bird, morning exam. Pass or fail? And: can one straight line separate passes from fails?"),
    code('my_prediction = {"Asha": "pass", "best line": 3}', stub='my_prediction = {"Asha": None, "best line": None}'),
    md("## 2 · The students"),
    code(CLOCK_DATA),
    md("## 3 · One clue alone is a coin flip"),
    code("""for col, name in [(0, 'exam time'), (1, 'body clock')]:
    for v in (0, 1):
        print(f'{name} = {v}: results {y[X[:, col] == v]}')"""),
    md("## 4 · One neuron = one straight cut\n$$\\text{pass if } w_1 x_1 + w_2 x_2 + b > 0$$"),
    code("""def neuron(w1, w2, b, X):
    return (X[:, 0] * w1 + X[:, 1] * w2 + b > 0).astype(float)

def right(w1, w2, b):
    return int(np.sum(neuron(w1, w2, b, X) == y))

print('line (1, -1, 0.5):', right(1, -1, 0.5), 'of 4')""",
         stub="""def neuron(w1, w2, b, X):
    # TODO: 1 where w1·x1 + w2·x2 + b > 0, else 0
    raise NotImplementedError

def right(w1, w2, b):
    return int(np.sum(neuron(w1, w2, b, X) == y))"""),
    md("## 5 · Search every line"),
    code("""grid = np.arange(-3, 3.01, 0.25)
scores = [right(a, b, c) for a in grid for b in grid for c in grid]
print(f'lines tried: {len(scores):,} · best: {max(scores)} of 4 · lines reaching 3: {scores.count(3):,}')"""),
    md("## 6 · PROOF"),
    code("""assert len(scores) == 15625 and max(scores) == 3, 'no straight line gets all four'
assert [right(*l) for l in [(1, 1, -0.5), (-1, -1, 1.5), (1, -1, 0.5), (0, 0, 1)]] == [1, 1, 3, 2], 'slide table'
assert my_prediction == {"Asha": "pass", "best line": 3}
print('✓ proof: 15,625 lines, best 3 of 4')"""),
    md("## 7 · Picture"),
    code("""colors = ['tab:green' if r else 'tab:red' for r in y]
plt.scatter(X[:, 0], X[:, 1], c=colors, s=600)
for n, (a, b) in zip(names, X):
    plt.annotate(n, (a, b), textcoords='offset points', xytext=(0, 22), ha='center')
xs = np.linspace(-0.3, 1.3, 2)
plt.plot(xs, xs + 0.5, color='tab:orange', label='best try: 3 of 4')
plt.xticks([0, 1], ['morning', 'evening']); plt.yticks([0, 1], ['early bird', 'night owl'])
plt.xlim(-0.4, 1.4); plt.ylim(-0.4, 1.4); plt.legend(); plt.show()"""),
    md("## 8 · Your turn\nChange the rule to “pass when both are 1” (y = [0, 1, 0, 0]). Can one line do it now?"),
    code("y_and = np.array([0, 1, 0, 0.])\nprint(max(int(np.sum(neuron(a, b, c, X) == y_and)) for a in grid for b in grid for c in grid))", stub="# TODO"),
    md("## Recap\nOne neuron draws one straight cut. The body-clock rule needs two clues together: no single line gets more than 3 of 4."),
]

NOTEBOOKS["ch19-hidden-clues"] = [
    md("""
# Chapter 19 · Hidden neurons invent new clues
**Deck 4 · Live demo.** Build a 2-2-1 network by hand: two hidden clues (“both evening?”, “both morning?”) and an output (“either?”).

**You will:** write one neuron · build the two clues · combine them · prove 4 of 4.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nWhich student turns on hidden neuron 2 (“both morning?”)?"),
    code('my_prediction = "Kabir"', stub="my_prediction = None"),
    code(CLOCK_DATA),
    md("## 2 · One neuron: weighted sum, then a switch"),
    code("""def neuron(x, w, b):
    z = x @ np.array(w) + b
    return z, (z > 0).astype(float)""",
         stub="""def neuron(x, w, b):
    # TODO: z = x · w + b ; return z and the switch (1 if z > 0)
    raise NotImplementedError"""),
    md("## 3 · The two invented clues and the output"),
    code("""z1, h1 = neuron(X, [1, 1], -1.5)      # both evening?
z2, h2 = neuron(X, [-1, -1], 0.5)     # both morning?
H = np.c_[h1, h2]
z3, out = neuron(H, [1, 1], -0.5)     # either clue?
for n, a, b, c, d, o in zip(names, z1, h1, z2, h2, out):
    print(f'{n:6} hidden1 z {a:+.1f} → {b:.0f} · hidden2 z {c:+.1f} → {d:.0f} · output {o:.0f}')"""),
    md("## 3b · Many weights work\nTry every w₁, w₂, b on a grid and count how many make a perfect “both evening?” neuron."),
    code("""grid = np.arange(-2, 2.01, 0.5)
want = np.array([0, 1, 0, 0])
good = [(a, b, c) for a in grid for b in grid for c in np.arange(-3, 3.01, 0.5)
        if np.array_equal(neuron(X, [a, b], c)[1], want)]
print(f'{len(good)} different (w1, w2, b) make a perfect “both evening?” neuron, e.g.', good[:4])
assert (1.0, 1.0, -1.5) in good and len(good) > 10
print('✓ no single right answer: many weights work')"""),
    md("## 3c · How many hidden neurons? Let training decide\nTrain sigmoid networks with 1, 2, 3, 4 and 8 hidden neurons, 50 random starts each (3,000 epochs, η = 1), and count the runs that get all four students right."),
    code("""sig = lambda z: 1 / (1 + np.exp(-z))
Y = y.astype(float)

def train(H, seed, epochs=3000, eta=1.0):
    r = np.random.default_rng(seed)
    W1, b1, W2, b2 = r.normal(0, 1, (2, H)), np.zeros(H), r.normal(0, 1, H), 0.0
    for _ in range(epochs):
        Hh = sig(X @ W1 + b1); P = sig(Hh @ W2 + b2); d2 = (P - Y) / 4
        dH = np.outer(d2, W2) * Hh * (1 - Hh)
        W2 -= eta * Hh.T @ d2; b2 -= eta * d2.sum(); W1 -= eta * X.T @ dH; b1 -= eta * dH.sum(0)
    P = sig(sig(X @ W1 + b1) @ W2 + b2)
    return int(((P >= 0.5) == (Y == 1)).sum())

sweep = {H: sum(train(H, s) == 4 for s in range(50)) for H in (1, 2, 3, 4, 8)}
for H, ok in sweep.items():
    print(f'{H} hidden: {ok:2d} of 50 runs learned all four')
assert sweep == {1: 0, 2: 39, 3: 46, 4: 50, 8: 50}, 'same table as the slide'
print('✓ too few can’t learn; a few spare make it reliable')"""),
    md("## 4 · PROOF"),
    code("""assert list(h1) == [0, 1, 0, 0] and list(h2) == [1, 0, 0, 0], 'each clue fires for one student'
assert list(out) == list(y), 'all four right'
assert names[int(np.argmax(h2))] == my_prediction
_, h1a = neuron(np.array([[0., 0.]]), [1, 1], -1.5); _, h2a = neuron(np.array([[0., 0.]]), [-1, -1], 0.5)
assert neuron(np.c_[h1a, h2a], [1, 1], -0.5)[1][0] == 1, 'Asha passes'
print('✓ proof: 4 of 4, Asha passes')"""),
    md("## 5 · Your turn\nBuild a network for “pass when they DON’T match” (y = [0, 0, 1, 1])."),
    code("# TODO", stub="# TODO"),
    md("## Recap\nHidden neurons turn raw inputs into new clues. With the right clues, the output needs only one straight cut."),
]

NOTEBOOKS["ch21-backprop-by-hand"] = [
    md("""
# Chapter 21 · Backpropagation by hand
**Deck 4 · Live demo.** x → w₁ → ReLU → w₂ → loss. Forward, backward link by link, check by nudging, one step.

**You will:** compute every forward value · pass the blame back · gradient-check · take one step (loss 4 → 0.25).
"""),
    code(SETUP),
    md("## 1 · Your prediction\nWith x = 2, y = 5, w₁ = 0.5, w₂ = 3: what is the slope for w₁?"),
    code("my_prediction = -24", stub="my_prediction = None"),
    md("## 2 · Forward pass: keep every value"),
    code("""x, y = 2.0, 5.0

def forward(w1, w2):
    z = w1 * x
    h = max(0.0, z)          # ReLU
    yhat = w2 * h
    loss = (yhat - y) ** 2
    return z, h, yhat, loss

z, h, yhat, loss = forward(0.5, 3.0)
print(f'z = {z} · h = {h} · ŷ = {yhat} · loss = {loss}')"""),
    md("## 3 · Backward pass: multiply local slopes, right to left\n$$\\frac{\\partial L}{\\partial w_1} = \\frac{\\partial L}{\\partial \\hat y}\\cdot\\frac{\\partial \\hat y}{\\partial h}\\cdot\\frac{\\partial h}{\\partial z}\\cdot\\frac{\\partial z}{\\partial w_1}$$"),
    code("""def backward(w1, w2):
    z, h, yhat, loss = forward(w1, w2)
    d_yhat = 2 * (yhat - y)            # loss per ŷ
    d_w2 = d_yhat * h                  # ŷ = w2 · h
    d_h = d_yhat * w2
    d_z = d_h * (1.0 if z > 0 else 0)  # ReLU slope
    d_w1 = d_z * x                     # z = w1 · x
    return d_yhat, d_w2, d_h, d_w1

print(backward(0.5, 3.0))""",
         stub="""def backward(w1, w2):
    z, h, yhat, loss = forward(w1, w2)
    # TODO: d_yhat, d_w2, d_h, d_w1, one link at a time
    raise NotImplementedError"""),
    md("## 4 · Gradient check: nudge each weight"),
    code("""eps = 0.01
nudge_w1 = (forward(0.5 + eps, 3)[3] - forward(0.5, 3)[3]) / eps
nudge_w2 = (forward(0.5, 3 + eps)[3] - forward(0.5, 3)[3]) / eps
print(f'nudge says w1 {nudge_w1:.2f}, w2 {nudge_w2:.2f}')"""),
    md("## 5 · One step of gradient descent"),
    code("""_, g2, _, g1 = backward(0.5, 3.0)
w1, w2 = 0.5 - 0.01 * g1, 3.0 - 0.01 * g2
print(f'w1 = {w1:.2f}, w2 = {w2:.2f}, loss {forward(0.5, 3)[3]} → {forward(w1, w2)[3]:.2f}')"""),
    md("## 6 · PROOF"),
    code("""assert forward(0.5, 3.0) == (1.0, 1.0, 3.0, 4.0)
assert backward(0.5, 3.0) == (-4.0, -4.0, -12.0, -24.0)
assert round(nudge_w1, 2) == -23.64 and round(nudge_w2, 2) == -3.99
assert (round(w1, 2), round(w2, 2), round(forward(w1, w2)[3], 2)) == (0.74, 3.04, 0.25)
assert my_prediction == -24
print('✓ proof: loss 4 · slopes −24, −4 · nudge agrees · one step → 0.25')"""),
    md("## 7 · Break it: a dead ReLU\nStart from w₁ = −0.5. What does backprop say for w₁, and why?"),
    code("print(backward(-0.5, 3.0), '→ z < 0, ReLU is off, no blame reaches w1')"),
    md("## Recap\nForward: keep every value. Backward: start at the loss, multiply local slopes link by link. Check by nudging."),
]

NOTEBOOKS["ch22-train-network"] = [
    md("""
# Chapter 22 · The network finds its own clues
**Deck 4 · Live demo.** Train the 2-2-1 network (sigmoid neurons, log loss, η = 1) from a fixed start, and open the box.

**You will:** write forward and backward for 9 numbers · train 3,000 epochs · prove the loss table · see the hidden clues it invented.
"""),
    code(SETUP),
    md("## 1 · Your prediction\nAt which epoch are all four students first on the right side of 0.5: 100, 500 or 1,000?"),
    code("my_prediction = 500", stub="my_prediction = None"),
    code(CLOCK_DATA),
    md("## 2 · Fixed starting weights (same as the slides)"),
    code("""sig = lambda z: 1 / (1 + np.exp(-z))
START = dict(W1=np.array([[0.5, -0.5], [0.4, -0.6]]), b1=np.array([0.1, 0.2]), W2=np.array([0.6, 0.7]), b2=0.0)

def forward(p):
    H = sig(X @ p['W1'] + p['b1'])
    P = sig(H @ p['W2'] + p['b2'])
    return H, P

def loss(p):
    P = forward(p)[1]
    return -np.mean(y * np.log(P) + (1 - y) * np.log(1 - P))

print('start P(pass):', forward(START)[1].round(2), '· loss', round(loss(START), 3))"""),
    md("## 3 · Backprop for all nine numbers\nWith sigmoid + log loss the output blame is simply (P − y) (Chapter 16). Then pass it back through W2 and each hidden sigmoid (slope h(1 − h))."),
    code("""def train(epochs, eta=1.0):
    p = {k: np.array(v, dtype=float) for k, v in START.items()}
    for _ in range(epochs):
        H, P = forward(p)
        d2 = (P - y) / len(y)                       # blame on the output
        gW2, gb2 = H.T @ d2, d2.sum()
        dH = np.outer(d2, p['W2']) * H * (1 - H)    # blame on each hidden neuron
        gW1, gb1 = X.T @ dH, dH.sum(axis=0)
        p['W1'] -= eta * gW1; p['b1'] -= eta * gb1; p['W2'] -= eta * gW2; p['b2'] -= eta * gb2
    return p""",
         stub="""def train(epochs, eta=1.0):
    p = {k: np.array(v, dtype=float) for k, v in START.items()}
    for _ in range(epochs):
        H, P = forward(p)
        # TODO: output blame (P − y)/4 → slopes for W2, b2 → hidden blame → slopes for W1, b1 → update
        pass
    return p"""),
    md("## 4 · The loss table"),
    code("""table = {}
for e in (0, 100, 300, 500, 1000, 3000):
    p = train(e)
    table[e] = (round(loss(p), 3), forward(p)[1].round(2))
    print(f'epoch {e:>5}: loss {table[e][0]:.3f} · P(pass) {table[e][1]}')"""),
    md("## 5 · PROOF"),
    code("""assert [table[e][0] for e in (0, 100, 300, 500, 1000, 3000)] == [0.748, 0.681, 0.472, 0.085, 0.017, 0.004]
first_all_right = next(e for e in (100, 300, 500, 1000) if np.all((table[e][1] >= 0.5) == (y == 1)))
assert first_all_right == my_prediction == 500
print('✓ proof: the slide table, all four right at epoch 500')"""),
    md("## 6 · Open the box: the hidden clues it invented"),
    code("""final = train(3000)
H, P = forward(final)
for n, h, pr in zip(names, H.round(2), P.round(3)):
    print(f'{n:6} hidden {h} · P(pass) {pr}')
print('W1', final['W1'].round(2).tolist(), 'b1', final['b1'].round(2), 'W2', final['W2'].round(2), 'b2', float(final['b2']).__round__(2))
assert H[1, 0] > 0.9 and H[0, 1] > 0.9, 'hidden 1 = both evening (Zara), hidden 2 = both morning (Kabir)'"""),
    md("## 7 · Picture"),
    code("""curve = [loss(train(e)) for e in range(0, 3001, 50)]
plt.plot(range(0, 3001, 50), curve); plt.xlabel('epoch'); plt.ylabel('log loss'); plt.title('plateau, then drop'); plt.show()"""),
    md("## 8 · Your turn\nTry other starting weights. Does it always find the same two clues? Does it always succeed?"),
    code("# TODO", stub="# TODO"),
    md("## Recap\nForward, blame back, step, repeat. The hidden neurons reinvented our hand-made clues, scaled up."),
]

NOTEBOOKS["ch23-pytorch"] = [
    md("""
# Chapter 23 · PyTorch does the bookkeeping
**Deck 4 · Live demo.** Rebuild Chapter 21’s chain and Chapter 22’s network in PyTorch, and match every number.

**You will:** use tensors with requires_grad · call backward() · train with the same five moves · prove the numbers match.
"""),
    code("import torch\nimport numpy as np\ntorch.set_default_dtype(torch.float64)\nprint(torch.__version__)"),
    md("## 1 · Your prediction\nAfter `loss.backward()`, what will `w1.grad` print?"),
    code("my_prediction = -24", stub="my_prediction = None"),
    md("## 2 · The chain, with autograd"),
    code("""x, y = torch.tensor(2.0), torch.tensor(5.0)
w1 = torch.tensor(0.5, requires_grad=True)
w2 = torch.tensor(3.0, requires_grad=True)

loss = (w2 * torch.relu(w1 * x) - y) ** 2   # the forward pass is recorded
loss.backward()                              # the blame game, automatically
print('loss', loss.item(), '· w1.grad', w1.grad.item(), '· w2.grad', w2.grad.item())"""),
    md("## 3 · The 2-2-1 network, same fixed start"),
    code("""X = torch.tensor([[0., 0.], [1., 1.], [1., 0.], [0., 1.]])
Y = torch.tensor([1., 1., 0., 0.])

model = torch.nn.Sequential(torch.nn.Linear(2, 2), torch.nn.Sigmoid(), torch.nn.Linear(2, 1), torch.nn.Sigmoid())
with torch.no_grad():                         # PyTorch stores weights as [out, in]
    model[0].weight.copy_(torch.tensor([[0.5, 0.4], [-0.5, -0.6]]))
    model[0].bias.copy_(torch.tensor([0.1, 0.2]))
    model[2].weight.copy_(torch.tensor([[0.6, 0.7]]))
    model[2].bias.copy_(torch.tensor([0.0]))

loss_fn = torch.nn.BCELoss()
opt = torch.optim.SGD(model.parameters(), lr=1.0)
print('start loss', round(loss_fn(model(X).squeeze(), Y).item(), 3))"""),
    md("## 4 · The training loop: our five moves"),
    code("""table = {}
for epoch in range(3001):
    pred = model(X).squeeze()        # forward
    loss = loss_fn(pred, Y)          # loss
    if epoch in (0, 100, 300, 500, 1000, 3000):
        table[epoch] = round(loss.item(), 3)
    opt.zero_grad()                  # clear last step's slopes
    loss.backward()                  # every slope
    opt.step()                       # every weight moves
print(table)""",
         stub="""table = {}
for epoch in range(3001):
    pred = model(X).squeeze()
    loss = loss_fn(pred, Y)
    if epoch in (0, 100, 300, 500, 1000, 3000):
        table[epoch] = round(loss.item(), 3)
    # TODO: zero_grad, backward, step
print(table)"""),
    md("## 5 · PROOF"),
    code("""assert loss_fn is not None
x2, y2 = torch.tensor(2.0), torch.tensor(5.0)
a = torch.tensor(0.5, requires_grad=True); b = torch.tensor(3.0, requires_grad=True)
l = (b * torch.relu(a * x2) - y2) ** 2; l.backward()
assert (l.item(), a.grad.item(), b.grad.item()) == (4.0, -24.0, -4.0), 'same as Chapter 21 by hand'
assert list(table.values()) == [0.748, 0.681, 0.472, 0.085, 0.017, 0.004], 'same loss table as NumPy (Chapter 22)'
assert my_prediction == a.grad.item()
print('✓ proof: autograd = the blame game; PyTorch matches NumPy to 3 decimals')"""),
    md("## 6 · Open the box"),
    code("""with torch.no_grad():
    print('hidden activations:', torch.sigmoid(model[0](X)).numpy().round(2))
    print('P(pass):', model(X).squeeze().numpy().round(3))"""),
    md("## 7 · Your turn\nSwap the hidden Sigmoid for ReLU (`torch.nn.ReLU()`). Train again. What changes?"),
    code("# TODO", stub="# TODO"),
    md("## Recap\n`loss.backward()` is the blame game. `opt.step()` is w ← w − η × slope. PyTorch only keeps the books."),
]


if __name__ == "__main__":
    paths = [build(name, cells) for name, cells in NOTEBOOKS.items()]
    print(f"wrote {len(paths)} solution notebooks + {len(paths)} starters")
    if "--run" in sys.argv:
        failed = []
        for p in paths:
            r = subprocess.run([str(HERE / ".venv/bin/jupyter"), "nbconvert", "--to", "notebook", "--execute", "--inplace", str(p)],
                               capture_output=True, text=True)
            print(("✓ " if r.returncode == 0 else "✗ ") + p.name)
            if r.returncode != 0:
                failed.append(p.name)
                print(r.stderr[-1500:])
        sys.exit(1 if failed else 0)
