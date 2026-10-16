"""
Builds the neural-network lab notebooks (education domain: Asha and her class).

Each notebook is written twice from one source:
  labs2/<name>.ipynb          solution (the trainer's live demo; every cell filled in)
  labs2/starter/<name>.ipynb  starter  (participants; solution cells replaced by TODO stubs)

Every notebook is a ladder: one new idea per step, concrete before abstract (by hand → name → formula),
each step ends with a ✓ check cell, then your turn → recap → appendix.

Run:  ../.venv/bin/python build_notebooks.py          (writes notebooks)
      ../.venv/bin/python build_notebooks.py --run    (also executes every solution notebook to prove it runs)
"""
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
SETUP = """import torch
torch.set_printoptions(precision=3, sci_mode=False)
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.figsize": (8, 4.5), "font.size": 12})"""


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

# ---------------------------------------------------------------- Lab 1 (simple)
NOTEBOOKS["01-self-attention"] = [
    md("""
# Lab 1 · Self-attention (simple)
The word **“she”** means nothing alone: you need to know *who*.
Self-attention lets each word **look at the other words and borrow from them**.

It is just three steps: **score → share → blend**.
"""),
    code("""import torch
import torch.nn as nn
import torch.nn.functional as F
torch.set_printoptions(precision=3, sci_mode=False)
torch.set_grad_enabled(False)   # no training in this lab"""),

    # ---- 1
    md("""
## 1 · Words as numbers
Each word gets 2 numbers: `[person, thing]`.
"""),
    code("""words = ['Asha', 'exam', 'she']
X = torch.tensor([[2., 0.],    # Asha: a person
                  [0., 2.],    # exam: a thing
                  [1., 0.]])   # she : a person, but who?
print(X)"""),

    # ---- 2
    md("""
## 2 · Score: how alike is *she* to each word?
Dot product: multiply matching numbers, add them up. Alike → big number.
"""),
    code("""she = X[2]
scores = X @ she
print(scores)        # she·Asha = 2, she·exam = 0, she·she = 1""",
         stub="""she = X[2]
scores = None        # TODO: X @ she
print(scores)"""),

    # ---- 3
    md("""
## 3 · Share: turn scores into percentages
Softmax makes the scores positive and adds them up to 1.
"""),
    code("""weights = torch.softmax(scores, dim=0)
for w, a in zip(words, weights):
    print(f'she → {w:4} {a:.0%}')""",
         stub="""weights = None   # TODO: torch.softmax(scores, dim=0)
for w, a in zip(words, weights):
    print(f'she → {w:4} {a:.0%}')"""),

    # ---- 4
    md("""
## 4 · Blend: mix the words using those percentages
*she* takes 67% of Asha + 9% of exam + 24% of herself.
"""),
    code("""she_new = weights @ X
print('she before:', X[2])
print('she after :', she_new)    # moved toward Asha""",
         stub="""she_new = None   # TODO: weights @ X
print('she before:', X[2])
print('she after :', she_new)"""),
    md("That’s self-attention for one word. ✓"),

    # ---- 5
    md("""
## 5 · All words at once
Do the same for every word in one go. The score table is **words × words** (3 × 3):
each row is one word scoring all 3 words.
"""),
    code("""scores  = X @ X.T                         # 3 × 3: every word scores every word
weights = torch.softmax(scores, dim=1)    # each row adds up to 1
out     = weights @ X                     # 3 × 2: every word, blended

print('weights (row = who looks, column = looked at):')
print(weights)
print('new vectors:')
print(out)""",
         stub="""scores  = None   # TODO: X @ X.T
weights = None   # TODO: softmax along each row (dim=1)
out     = None   # TODO: weights @ X
print(weights)
print(out)"""),
    md("Row 3 is *she*: the same numbers as steps 2–4."),

    # ---- 6
    md("""
## 6 · Query, Key, Value
So far each word used **its own vector** for everything. Real models make **3 versions** of each word,
each with its own learned layer:

| | Meaning | Library analogy |
| --- | --- | --- |
| **Query** Q | what I’m looking for | my question |
| **Key** K | what I offer | the label on a book |
| **Value** V | what I hand over | what’s inside the book |

Score with Q and K, blend the V’s. Same three steps.
"""),
    code("""torch.manual_seed(0)
W_Q, W_K, W_V = nn.Linear(2, 2, bias=False), nn.Linear(2, 2, bias=False), nn.Linear(2, 2, bias=False)
Q, K, V = W_Q(X), W_K(X), W_V(X)          # random now; training would learn them

weights = torch.softmax(Q @ K.T, dim=1)   # score + share
out     = weights @ V                     # blend
print(weights)"""),

    # ---- 7
    md("""
## 7 · The full formula
One last detail: divide the scores by **√d** (d = how many numbers each word has, here 2).
Real words have hundreds of numbers, which makes scores huge; dividing keeps softmax from putting 100% on one word.

$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{Q K^\\top}{\\sqrt{d}}\\right) V$$
"""),
    code("""def attention(Q, K, V):
    d = K.shape[-1]
    weights = torch.softmax(Q @ K.mT / d ** 0.5, dim=-1)   # score + share
    return weights @ V                                     # blend

mine    = attention(Q, K, V)
pytorch = F.scaled_dot_product_attention(Q, K, V)          # PyTorch’s built-in
print(mine)
print('same as PyTorch?', torch.allclose(mine, pytorch))""",
         stub="""def attention(Q, K, V):
    d = K.shape[-1]
    weights = None   # TODO: softmax(Q @ K.mT / √d) along the last dim
    return weights @ V

mine    = attention(Q, K, V)
pytorch = F.scaled_dot_product_attention(Q, K, V)
print(mine)
print('same as PyTorch?', torch.allclose(mine, pytorch))"""),

    # ---- recap
    md("""
## Recap
1. **Score**: each word’s query · every word’s key
2. **Share**: softmax → percentages that add up to 1
3. **Blend**: mix the values with those percentages

That’s self-attention. A Transformer stacks this layer many times.

**Try it:** change *she* to `[1., 1.]` in step 1 (a bit person, a bit thing) and re-run. Who does she look at now?
"""),
]

# ---------------------------------------------------------------- Lab 1 (full)
NOTEBOOKS["01-self-attention-full"] = [
    md("""
# Lab 1 · Self-attention
A word on its own doesn’t know what it means: **“she”** only makes sense once you know *who*.
Self-attention lets every word look at every other word and borrow what it needs.

We climb one step at a time. Each step adds **one** new idea, and ends with a ✓ check.

| Step | New idea |
| --- | --- |
| 0 | a word is a vector |
| 1 | score: how alike are two words? |
| 2 | share: turn scores into weights |
| 3 | blend: mix the words with those weights |
| 4 | all words at once: one function |
| 5 | the problem: words only find look-alikes |
| 6 | the fix: each word gets its own question (query, key, value) |
| 7 | bigger vectors: divide by √d |
| 8 | let training find the weights |
| 9 | look inside the trained model |
"""),
    code(SETUP),
    code("""# helper: draws an attention table (just run it)
def plot_attention(A, labels, title):
    A = A.detach()
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.imshow(A, cmap='Blues', vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=30); ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel('looked at'); ax.set_ylabel('who is looking')
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f'{A[i, j]:.2f}', ha='center', va='center', color='white' if A[i, j] > 0.6 else '#333')
    ax.set_title(title); plt.show()"""),

    # ---- 0 · words as numbers
    md("""
## Step 0 · A word is a vector
A network can’t read letters, so every word becomes a short list of numbers.
For now we use **two clues** per word, `[person, thing]`, and pick the numbers by hand:

| word | person | thing |
| --- | --- | --- |
| Asha | 2 | 0 |
| exam | 0 | 2 |
| she  | 1 | 0 |

*she* gets only 1 for “person”: it is a person, but on its own it doesn’t say **who**.

Each word here has **2 numbers**. That count has a short name we’ll use later: **d** (so here **d = 2**).
"""),
    code("""words = ['Asha', 'exam', 'she']
X = torch.tensor([[2., 0.],    # Asha
                  [0., 2.],    # exam
                  [1., 0.]])   # she
print(X)"""),
    md("""
Real models don’t type these numbers. They start every word at **random** numbers and let training move them:

```python
emb = nn.Embedding(num_embeddings=3, embedding_dim=2)   # 3 words × 2 numbers, random at first
```

The **Appendix** at the end trains one and shows *she* landing next to *Asha* on its own.
"""),
    code("""n_words, d = X.shape          # d = how many numbers each word has
assert (n_words, d) == (3, 2)
print(f'✓ step 0: {n_words} words, d = {d} numbers each')"""),

    # ---- 1 · score
    md("""
## Step 1 · Score: how alike are two words?
The **dot product** multiplies matching clues and adds them up. Alike words → big score.

*she · Asha* = 1×2 + 0×0 = **2** · *she · exam* = 1×0 + 0×2 = **0** · *she · she* = 1×1 + 0×0 = **1**
"""),
    code("""q = X[2]                         # she is the one looking
scores = X @ q                   # she · every word
for w, s in zip(words, scores):
    print(f'she · {w:4} = {s:.3f}')""",
         stub="""q = X[2]                         # she is the one looking
scores = None                    # TODO: X @ q  (dot product of every word with she)
for w, s in zip(words, scores):
    print(f'she · {w:4} = {s:.3f}')"""),
    code("""assert torch.equal(scores, torch.tensor([2., 0., 1.]))
print('✓ step 1: she is most like Asha')"""),

    # ---- 2 · share
    md("""
## Step 2 · Share: turn scores into weights
*she* has 100% attention to give out. **Softmax** does the sharing: `exp(score) / sum of exp(scores)`.
Bigger score → bigger share, every share positive, all shares add up to 1.

**Predict first:** what share goes to Asha?
"""),
    code("my_prediction = 0.6   # ← your guess, between 0 and 1", stub="my_prediction = None   # ← your guess, between 0 and 1"),
    code("""weights = torch.exp(scores) / torch.exp(scores).sum()
for w, a in zip(words, weights):
    print(f'she → {w:4} {a:.3f}  ' + '█' * int(a * 40))""",
         stub="""weights = None   # TODO: torch.exp(scores) divided by its sum
for w, a in zip(words, weights):
    print(f'she → {w:4} {a:.3f}  ' + '█' * int(a * 40))"""),
    code("""assert torch.allclose(weights, torch.tensor([0.665, 0.090, 0.245]), atol=1e-3)
assert torch.isclose(weights.sum(), torch.tensor(1.0))
print(f'✓ step 2: she gives {weights[0]:.1%} to Asha (you guessed {my_prediction})')"""),

    # ---- 3 · blend
    md("""
## Step 3 · Blend: mix the words with those weights
*she*’s new vector = 0.665 × Asha + 0.090 × exam + 0.245 × she.
"""),
    code("""she_new = weights @ X
print('she before:', X[2], '→ after:', she_new)""",
         stub="""she_new = None   # TODO: weights @ X
print('she before:', X[2], '→ after:', she_new)"""),
    code("""assert she_new[0] > X[2, 0]
print(f'✓ step 3: she borrowed “person” from Asha: 1.0 → {she_new[0]:.3f}')"""),
    md("That is self-attention for one word: **score → share → blend**. Everything else is doing it for every word, and choosing the scores well."),

    # ---- 4 · all words
    md("""
## Step 4 · All words at once
> **So far:** *she* looked at every word: score → share → blend.
> **Now:** let **every** word do the same thing, not just *she*.

First the slow way: a loop, one word at a time. Each line is step 1 again, for a different word.
"""),
    code("""for i, w in enumerate(words):
    print(f'{w:4} scores:', X @ X[i])"""),
    md("""
The fast way gives the same numbers in one go: `X @ X.mT`. (`.mT` turns X on its side, so every row meets every row.)
Row 3 is *she*: exactly step 1.
"""),
    code("""print(X @ X.mT)"""),
    md("""
**Wait: X had 2 columns, why does this have 3?** Because the columns are now **words**, not clues.

| Table | Rows | Columns |
| --- | --- | --- |
| `X` | 3 words | 2 clues `[person, thing]` |
| `X @ X.mT` | 3 words (who is looking) | 3 words (who is looked at) |

Every word scores every word, so 3 words × 3 words gives 3 × 3. The 2 clues are used up inside each dot product
(multiply and add). They come back after blending (step 3), when the output is 2 numbers per word again.
"""),
    code("""print('X          ', tuple(X.shape), '  3 words × 2 clues')
print('X.mT       ', tuple(X.mT.shape), '  2 clues × 3 words  (X on its side)')
print('X @ X.mT   ', tuple((X @ X.mT).shape), '  3 words × 3 words  (the scores)')
print('weights @ X', tuple((torch.softmax(X @ X.mT, dim=-1) @ X).shape), '  3 words × 2 clues  (blended: back to 2)')"""),
    md("""
Now wrap steps 1–3 into one function. We give it three inputs, **Q**, **K**, **V**. For now all three are just `X`;
step 6 shows why they get different names.
"""),
    code("""def attention(Q, K, V):
    scores  = Q @ K.mT                          # step 1: every word scores every word
    weights = torch.softmax(scores, dim=-1)     # step 2: each row shares out 100%
    return weights @ V, weights                 # step 3: blend

out, A = attention(X, X, X)
plot_attention(A, words, 'Each row = one word sharing its attention')""",
         stub="""def attention(Q, K, V):
    scores  = None   # TODO: Q @ K.mT   (step 1 for every word)
    weights = None   # TODO: torch.softmax(scores, dim=-1)   (step 2)
    return weights @ V, weights                 # step 3: blend

out, A = attention(X, X, X)
plot_attention(A, words, 'Each row = one word sharing its attention')"""),
    code("""assert torch.allclose(A[2], weights), 'the she row is exactly steps 1-2'
assert torch.allclose(A.sum(dim=1), torch.ones(3)), 'every row shares out 100%'
print('✓ step 4: the she row = steps 1–3; every row shares out 100%')"""),

    # ---- 5 · the problem
    md("""
## Step 5 · The problem: words only find look-alikes
> **So far:** every word scores every word with its own vector.
> **Now:** notice what that can’t do.

Read the heatmap row by row:
- **Asha** looks at Asha (0.87)
- **exam** looks at exam (0.96)
- **she** looks at Asha (0.67), a word that looks like her

A word’s vector is both *what it is* and *what it asks for*, so the only question it can ask is **“who looks like me?”**.
But *exam* doesn’t need more exam. It needs **who took it**: a person, the opposite of what it is.
"""),
    code("""for i, w in enumerate(words):
    print(f'{w:4} looks mostly at {words[A[i].argmax()]}')
assert all(A[i].argmax() in (i, 0) for i in range(3))
print('✓ step 5: every word finds itself or a look-alike')"""),

    # ---- 6 · query
    md("""
## Step 6 · The fix: give each word its own question
> **So far:** a word’s question = its own vector.
> **Now:** make the question a **separate** vector, called the **query**: `Q = X @ W_Q`.

`W_Q` is a small matrix that turns *what I am* into *what I’m looking for*.
Try one by hand that **swaps the two clues**: `[person, thing]` → `[thing, person]`.
"""),
    code("""W_Q = torch.tensor([[0., 1.],
                    [1., 0.]])     # swap the two clues
Q = X @ W_Q

kind = lambda v: 'a person' if v[0] > v[1] else 'a thing'
for i, w in enumerate(words):
    print(f'{w:4} is {kind(X[i]):8}  → asks for {kind(Q[i])}')""",
         stub="""W_Q = None   # TODO: a 2×2 matrix that swaps the two clues
Q = X @ W_Q

kind = lambda v: 'a person' if v[0] > v[1] else 'a thing'
for i, w in enumerate(words):
    print(f'{w:4} is {kind(X[i]):8}  → asks for {kind(Q[i])}')"""),
    md("Same `attention` function. The only change: pass `Q` as the question, keep `X` for the rest."),
    code("""out_q, A_q = attention(Q, X, X)
plot_attention(A_q, words, 'With W_Q: each word asks for the other kind')"""),
    code("""assert words[A_q[1].argmax()] == 'Asha' and round(A_q[1, 0].item(), 3) == 0.867
assert words[A_q[0].argmax()] == 'exam' and round(A_q[0, 1].item(), 3) == 0.965
print(f'✓ step 6: exam now finds who took it (Asha {A_q[1, 0]:.3f}); Asha finds what she took (exam {A_q[0, 1]:.3f})')"""),
    md("""
One small matrix changed **what each word asks for**. The same trick works for the other two inputs:

| Name | Made by | Library analogy | In our function |
| --- | --- | --- | --- |
| **Query** | `X @ W_Q` | the question I ask | 1st input |
| **Key** | `X @ W_K` | the label on each book’s spine | 2nd input |
| **Value** | `X @ W_V` | what’s inside the book | 3rd input |

That is where the names Q, K, V come from. Here we only changed Q.

Look at *she* though: it now asks for a thing, which is wrong for a pronoun. One hand-made W_Q can’t suit every word,
so in step 8 we let **training** find W_Q, W_K and W_V.
"""),

    # ---- 7 · √d
    md("""
## Step 7 · Bigger vectors: divide by √d
> **So far:** words with d = 2 numbers each.
> **Now:** real words have d = 64 to 768 numbers. One small fix is needed.

**The problem in one picture:** softmax of small scores shares out; softmax of big scores picks one word.
"""),
    code("""print('scores  2,  1, 0 →', torch.softmax(torch.tensor([2., 1., 0.]), dim=0))
print('scores 20, 10, 0 →', torch.softmax(torch.tensor([20., 10., 0.]), dim=0))"""),
    md("""
**Why scores get big:** a dot product adds up **d** products. More numbers per word → bigger scores.
Watch the typical score size for random words as d grows, and what dividing by √d does:
"""),
    code("""torch.manual_seed(0)
for d_big in (2, 16, 128, 512):
    q, K = torch.randn(d_big), torch.randn(10000, d_big)    # one word scoring 10,000 random words
    s = K @ q
    print(f'd = {d_big:3}   typical score size {s.std():5.1f}   after ÷ √d {(s / d_big ** 0.5).std():.1f}')"""),
    md("""
Dividing by √d brings scores back to about 1 at any size, so softmax keeps sharing. Add it to our function:

$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{Q K^\\top}{\\sqrt{d}}\\right) V$$
"""),
    code("""def attention(Q, K, V):
    d = K.shape[-1]                             # numbers per word
    scores  = Q @ K.mT / d ** 0.5               # step 1, now ÷ √d
    weights = torch.softmax(scores, dim=-1)     # step 2
    return weights @ V, weights                 # step 3""",
         stub="""def attention(Q, K, V):
    d = K.shape[-1]                             # numbers per word
    scores  = None   # TODO: same as step 4, then divide by d ** 0.5
    weights = torch.softmax(scores, dim=-1)
    return weights @ V, weights"""),
    code("""assert torch.allclose(attention(X, X, X)[0], F.scaled_dot_product_attention(X, X, X))
print('✓ step 7: our attention = PyTorch’s scaled_dot_product_attention (“scaled” = ÷ √d)')"""),

    # ---- 8 · train
    md("""
## Step 8 · Let training find the weights
> **So far:** 3 words, one hand-made W_Q.
> **Now:** a real task where the model must learn **W_Q, W_K, W_V** by itself.

**The task.** The teacher lists 4 students with their grades in a random order, then asks about one:

```
Meena:B   Asha:D   Kiran:A   Ravi:C   Kiran?      → answer A
```

The last token, **Kiran?**, must find Kiran’s row and copy the grade. That is a job for attention.
"""),
    code("""# helper: builds random registers (just run it)
STUDENTS, GRADES = ['Asha', 'Ravi', 'Meena', 'Kiran'], ['A', 'B', 'C', 'D']
D = 4 + 4 + 1

def make_registers(n, seed):
    g = torch.Generator().manual_seed(seed)
    X, y = torch.zeros(n, 5, D), torch.zeros(n, dtype=torch.long)
    for b in range(n):
        order, grades = torch.randperm(4, generator=g), torch.randint(0, 4, (4,), generator=g)
        for row in range(4):
            X[b, row, order[row]] = 1
            X[b, row, 4 + grades[row]] = 1
        ask = torch.randint(0, 4, (1,), generator=g).item()
        X[b, 4, ask] = 1
        X[b, 4, -1] = 1
        y[b] = grades[(order == ask).nonzero().item()]
    return X, y

def show(x):
    names = [STUDENTS[t[:4].argmax()] for t in x]
    return [f'{n}:{GRADES[t[4:8].argmax()]}' for n, t in zip(names[:4], x[:4])] + [names[4] + '?']

X_train, y_train = make_registers(4000, seed=0)
X_test,  y_test  = make_registers(1000, seed=1)
for i in range(3):
    print('  '.join(show(X_test[i])), '   → answer', GRADES[y_test[i]])"""),
    md("""
**What a token looks like.** Same idea as step 0, just more clues: each token is **9 numbers**.
A 1 marks *which name*, *which grade*, and whether it is *the question*:
"""),
    code("""header = STUDENTS + GRADES + ['?']
print(' ' * 9 + ' '.join(f'{h:>5}' for h in header))
for label, row in zip(show(X_test[0]), X_test[0]):
    print(f'{label:8} ' + ' '.join(f'{int(v):>5}' for v in row))"""),
    md("""
**The model** is our step 7 `attention`, with W_Q, W_K, W_V as three `nn.Linear` layers that start random.
A readout turns the question token’s output into 4 grade scores.

The rival has **no attention**: it averages all 5 tokens.
"""),
    code("""class SelfAttention(nn.Module):
    def __init__(self, d_in, d=8):               # d_in = 9 numbers per token in, d = 8 numbers inside attention
        super().__init__()
        self.W_Q = nn.Linear(d_in, d, bias=False)
        self.W_K = nn.Linear(d_in, d, bias=False)
        self.W_V = nn.Linear(d_in, d, bias=False)
        self.readout = nn.Linear(d, 4)

    def forward(self, X):
        out, self.A = attention(self.W_Q(X), self.W_K(X), self.W_V(X))
        return self.readout(out[:, -1])          # answer at the question token (last position)

class Averager(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, 32), nn.ReLU(), nn.Linear(32, 4))

    def forward(self, X):
        return self.net(X.mean(dim=1))           # every token counts the same""",
         stub="""class SelfAttention(nn.Module):
    def __init__(self, d_in, d=8):               # d_in = 9 numbers per token in, d = 8 numbers inside attention
        super().__init__()
        # TODO: self.W_Q, self.W_K, self.W_V = three nn.Linear(d_in, d, bias=False)
        self.readout = nn.Linear(d, 4)

    def forward(self, X):
        out, self.A = None, None   # TODO: attention(...) on W_Q(X), W_K(X), W_V(X)
        return self.readout(out[:, -1])

class Averager(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, 32), nn.ReLU(), nn.Linear(32, 4))

    def forward(self, X):
        return self.net(X.mean(dim=1))"""),
    md("**Predict first:** the averager sees the same tokens. Will it do as well?"),
    code("""def train(model, epochs=40):
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    history = []
    for epoch in range(epochs):
        for i in range(0, len(X_train), 200):
            loss = F.cross_entropy(model(X_train[i:i+200]), y_train[i:i+200])
            opt.zero_grad()
            loss.backward()
            opt.step()
        with torch.no_grad():
            history.append((model(X_test).argmax(1) == y_test).float().mean().item())
    return history

torch.manual_seed(0); attn_model = SelfAttention(D); attn_hist = train(attn_model)
torch.manual_seed(0); avg_model  = Averager(D);      avg_hist  = train(avg_model)

plt.plot(range(1, 41), attn_hist, lw=2, color='#2a78d6', label='self-attention')
plt.plot(range(1, 41), avg_hist, lw=2, color='#9a9a9a', label='averager (no attention)')
plt.axhline(0.25, ls=':', color='#555'); plt.text(40, 0.27, 'pure guess', ha='right', color='#555')
plt.ylim(0, 1.05); plt.xlabel('epoch'); plt.ylabel('test accuracy'); plt.grid(alpha=0.3)
plt.legend(frameon=False); plt.title('Reading the register'); plt.show()""",
         stub="""def train(model, epochs=40):
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    history = []
    for epoch in range(epochs):
        for i in range(0, len(X_train), 200):
            loss = F.cross_entropy(model(X_train[i:i+200]), y_train[i:i+200])
            # TODO: zero_grad, backward, step
        with torch.no_grad():
            history.append((model(X_test).argmax(1) == y_test).float().mean().item())
    return history

torch.manual_seed(0); attn_model = SelfAttention(D); attn_hist = train(attn_model)
torch.manual_seed(0); avg_model  = Averager(D);      avg_hist  = train(avg_model)

plt.plot(range(1, 41), attn_hist, lw=2, color='#2a78d6', label='self-attention')
plt.plot(range(1, 41), avg_hist, lw=2, color='#9a9a9a', label='averager (no attention)')
plt.axhline(0.25, ls=':', color='#555'); plt.text(40, 0.27, 'pure guess', ha='right', color='#555')
plt.ylim(0, 1.05); plt.xlabel('epoch'); plt.ylabel('test accuracy'); plt.grid(alpha=0.3)
plt.legend(frameon=False); plt.title('Reading the register'); plt.show()"""),
    code("""assert attn_hist[-1] > 0.98 and avg_hist[-1] < 0.65
print(f'✓ step 8: self-attention {attn_hist[-1]:.0%} · averager {avg_hist[-1]:.0%}')"""),
    md("The averager mixes every name with every grade, so it can’t tell *whose* grade is whose. It can only guess the most common one."),

    # ---- 9 · look inside
    md("## Step 9 · Look inside\nWhere does the question token look? Check the **bottom row**."),
    code("""with torch.no_grad():
    attn_model(X_test[:1])
labels = show(X_test[0])
print('  '.join(labels), '   → answer', GRADES[y_test[0]])
plot_attention(attn_model.A[0], labels, 'Learned attention')"""),
    code("""asked_row = labels.index(next(l for l in labels[:4] if l.startswith(labels[4][:-1] + ':')))
assert attn_model.A[0, 4].argmax() == asked_row
print(f'✓ step 9: the question puts {attn_model.A[0, 4, asked_row]:.0%} of its attention on {labels[asked_row]}')"""),
    md("Nobody told the model to match names. Training found a W_Q and W_K where *“Ravi?”* asks for Ravi and Ravi’s row answers."),

    # ---- your turn
    md("""
## Your turn
1. **No peeking ahead.** A model that writes left to right must not look at later words. In `attention` (step 7), before softmax add
   `scores = scores.masked_fill(torch.triu(torch.ones_like(scores), 1).bool(), float('-inf'))`.
   Re-run steps 4–7: what does *Asha* look at now?
2. **A better W_Q.** In step 6, find a W_Q where *exam* still looks at Asha but *she* also looks at Asha.
3. **Bigger class.** Make the class 8 students. Which model suffers more?
"""),
    code("# TODO", stub="# TODO"),

    # ---- recap
    md("""
## Recap
| Step | What you now know |
| --- | --- |
| 0 | a word is a vector of **d** numbers (learned by `nn.Embedding`) |
| 1–3 | self-attention = **score → share → blend** |
| 4 | all words at once: `softmax(Q @ K.mT) @ V` |
| 5–6 | W_Q lets a word ask for something different from what it is; W_K and W_V do the same for keys and values |
| 7 | bigger d → bigger scores, so divide by √d: `softmax(QKᵀ / √d) · V` |
| 8–9 | training finds the W’s; attention picks the right token, averaging can’t |

**Next:** attention ignores word order (“Asha beat Ravi” = “Ravi beat Asha”). Positional encoding fixes that.
"""),

    # ---- appendix
    md("""
## Appendix · Where do word vectors come from?
In step 0 I typed the numbers. A real model **learns** them:

1. Give every word a row of **random** numbers: `nn.Embedding(vocab_size, 2)`.
2. Train on a simple job: **read a word, guess the next word**.
3. Backprop nudges each word’s row. Words that are followed by the same words get pushed to the same place.

Nobody ever tells the model what a “person” or a “thing” is.
"""),
    code("""people = ['asha', 'ravi', 'meena', 'kiran', 'she', 'he']
verbs  = ['passed', 'failed', 'wrote', 'studied']
things = ['exam', 'quiz', 'test']
sentences = [f'{p} {v} the {t} .' for p in people for v in verbs for t in things]
print(len(sentences), 'sentences, e.g.', sentences[0], '|', sentences[-1])

vocab = sorted({w for s in sentences for w in s.split()})
ids = {w: i for i, w in enumerate(vocab)}
pairs = [(ids[a], ids[b]) for s in sentences for a, b in zip(s.split(), s.split()[1:])]   # (word, next word)
x = torch.tensor([a for a, _ in pairs])
y = torch.tensor([b for _, b in pairs])
print(len(vocab), 'words ·', len(pairs), 'training pairs, e.g.', vocab[x[0]], '→', vocab[y[0]])"""),
    code("""torch.manual_seed(0)
emb  = nn.Embedding(len(vocab), 2)      # the word vectors: 2 numbers per word, random at first
head = nn.Linear(2, len(vocab))         # turns a word vector into scores for the next word
before = emb.weight.detach().clone()

opt = torch.optim.Adam([*emb.parameters(), *head.parameters()], lr=0.05)
for step in range(300):
    loss = F.cross_entropy(head(emb(x)), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
after = emb.weight.detach()
for w in ['asha', 'she', 'exam']:
    print(f'{w:5} random start {before[ids[w]]}  →  learned {after[ids[w]]}')""",
         stub="""torch.manual_seed(0)
emb  = nn.Embedding(len(vocab), 2)
head = nn.Linear(2, len(vocab))
before = emb.weight.detach().clone()

opt = torch.optim.Adam([*emb.parameters(), *head.parameters()], lr=0.05)
for step in range(300):
    loss = None   # TODO: cross_entropy of head(emb(x)) against y
    # TODO: zero_grad, backward, step
after = emb.weight.detach()
for w in ['asha', 'she', 'exam']:
    print(f'{w:5} random start {before[ids[w]]}  →  learned {after[ids[w]]}')"""),
    code("""groups = {'people': (people, '#2a78d6'), 'things': (things, '#eb6834'),
          'verbs': (verbs, '#1baf7a'), 'the / .': (['the', '.'], '#888888')}

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for name, (ws, color) in groups.items():
    for ax, V in [(axes[0], before), (axes[1], after)]:
        pts = V[[ids[w] for w in ws]]
        ax.scatter(pts[:, 0], pts[:, 1], s=60, color=color, edgecolor='white', linewidth=2, zorder=3, label=name)
    for w in ws:                                             # before: label every word
        axes[0].annotate(w, before[ids[w]], xytext=(5, 5), textcoords='offset points', fontsize=10, color='#333')
    for w in ws if len(ws) < 3 else []:                      # after: small groups get word labels
        axes[1].annotate(w, after[ids[w]], xytext=(6, 4), textcoords='offset points', fontsize=10, color='#333')
    if len(ws) >= 3:                                         # after: big groups get one label listing their words
        pts = after[[ids[w] for w in ws]]
        c = (pts[:, 0].min().item(), pts[:, 1].mean().item())   # left edge of the cluster
        axes[1].annotate('\\\\n'.join(ws), c, xytext=(-14, 0), textcoords='offset points', ha='right', va='center',
                         fontsize=10, color='#333')
axes[0].set_title('Before training: random'); axes[1].set_title('After training: groups appear')
axes[1].set_xlim(after[:, 0].min() - 1.5, after[:, 0].max() + 0.5)
for ax in axes: ax.grid(alpha=0.3)
axes[0].legend(loc='upper left', frameon=False, fontsize=10)
plt.tight_layout(); plt.show()"""),
    code("""dist = lambda a, b: (after[ids[a]] - after[ids[b]]).norm().item()
print(f'distance she↔asha {dist("she", "asha"):.2f}   she↔exam {dist("she", "exam"):.2f}   exam↔quiz {dist("exam", "quiz"):.2f}')
assert dist('she', 'asha') < 1 < 4 < dist('she', 'exam')
print('✓ appendix: she learned to sit with the names, far from exam')"""),
    md("""
**she** lands next to **asha** and the other names because they are all followed by *passed / failed / wrote / studied*.
**exam / quiz / test** group together because they are all followed by “.”.
A word vector is just **numbers that place words used the same way close together**.
The `[person, thing]` table in step 0 is a hand-drawn version of the right-hand picture.
"""),
]


if __name__ == "__main__":
    paths = [build(name, cells) for name, cells in NOTEBOOKS.items()]
    print(f"wrote {len(paths)} solution notebooks + {len(paths)} starters")
    if "--run" in sys.argv:
        failed = []
        for p in paths:
            r = subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(p)],
                               capture_output=True, text=True)
            print(("✓ " if r.returncode == 0 else "✗ ") + p.name)
            if r.returncode != 0:
                failed.append(p.name)
                print(r.stderr[-1500:])
        sys.exit(1 if failed else 0)
