# Labs — AI from zero (education domain)

One notebook per demo slide. The **solution** notebook (this folder) is the trainer's live demo; the **starter** (`starter/`) has `# TODO` cells for participants.

| Notebook | Deck · chapter | What it proves |
| --- | --- | --- |
| `ch02-rules-vs-learning` | Deck 1 · Ch 2 | 75% rule → 5 of 8 wrong · doing nothing → 4 · best attendance → 3 · under 4 hours → 0 |
| `ch04-fit-the-line` | Deck 1 · Ch 4 | bad rule loss 33 · your rule loss 0 · Asha → 80 · Σ unrolled · hot or cold (w = 4 and 6 tie at 18.7) |
| `ch06-next-word` | Deck 1 · Ch 6 | the → exam 50% · passed the → exam 75% · failed the → quiz 100% · ravi → passed → the → exam |
| `ch10-gradient-descent` | Deck 2 · Ch 10 | slopes −506.7 / −120 · step 1 → 5.07, 1.20 · w overshoots past 12 · ends at 5, 40 · ~1,604 steps |
| `ch11-step-size` | Deck 2 · Ch 11 | 16,057 / 1,604 / 400 / explodes · cliff ≈ 0.0512 |
| `ch12-mini-batch` | Deck 2 · Ch 12 | 1,000 noisy students, 50,000 looks each: whole school 50 steps → loss 218.46 · mini-batch 32 → 1,563 steps, w 5.03 b 39.95, loss 10.02 (floor 10.01) · one student → 18.81 |
| `ch13-two-clues` | Deck 3 · Ch 13 | w₁ = 5, w₂ = 4, b = 32 → Asha 80 (also with scikit-learn) |
| `ch14-curves` | Deck 3 · Ch 14 | best line flat at 65, loss 70 · with sleep²: 20, −1.25, −5 · 7 h → 73.75 |
| `ch15-pass-fail` | Deck 3 · Ch 15–16 | Asha 0.995 · Ravi 0.5 · log loss 0.005 / 0.693 / 3.912 · learned boundary in the gap |
| `ch17-rare-cases` | Deck 3 · Ch 17 | 2 · 3 · 1 · 94 · accuracy 96% < lazy 97% · recall 67% · precision 40% |
| `ch18-no-straight-line` | Deck 4 · Ch 18 | each clue alone 50/50 · 15,625 straight lines tried, best 3 of 4 |
| `ch19-hidden-clues` | Deck 4 · Ch 19 | hand-built 2-2-1: “both evening”, “both morning”, “either” → 4 of 4, Asha passes |
| `ch21-backprop-by-hand` | Deck 4 · Ch 21 | loss 4 · slopes −24, −4 · nudge −23.64, −3.99 · one step → 0.25 · dead ReLU |
| `ch22-train-network` | Deck 4 · Ch 22 | loss 0.748 → 0.681 → 0.472 → 0.085 → 0.017 → 0.004 · all right at epoch 500 · hidden clues found |
| `ch23-pytorch` | Deck 4 · Ch 23 | `backward()` gives −24, −4 · PyTorch loss table = NumPy to 3 decimals (needs `torch`) |

Every notebook: your prediction → idea → math → by hand → NumPy → **proof cell (asserts the slide numbers)** → picture → break it → your turn → recap.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/jupyter lab
```

## Rebuild / verify

`build_notebooks.py` is the single source for all notebooks:

```bash
.venv/bin/python build_notebooks.py --run    # writes solution + starter notebooks and executes every solution
```
