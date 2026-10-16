# Labs 2 — Neural networks, one idea per notebook (education domain)

The **solution** notebook (this folder) is the trainer's live demo; the **starter** (`starter/`) has `# TODO` cells for participants.

| Notebook | Topic | What it proves |
| --- | --- | --- |
| `01-self-attention` | Self-attention, simple (19 cells) | words as numbers → score → share (she → Asha 67%) → blend → all words at once (3×3 table) → Query/Key/Value with `nn.Linear` → `softmax(QKᵀ/√d)V` = `F.scaled_dot_product_attention` |
| `01-self-attention-full` | Self-attention, full ladder (PyTorch) | 10-step ladder: word vectors → score → share (she → Asha 0.665) → blend → one `attention()` function → look-alike problem → swapped W_Q (exam → Asha 0.867) → d = numbers per word, ÷√d (= `F.scaled_dot_product_attention`) → trained attention 100% vs averaging 52% → learned focus on the asked row · appendix: `nn.Embedding` learns she ≈ asha |

Every notebook is a ladder: **one new idea per step**, concrete before abstract (by hand → name it → formula), and **every step ends with a ✓ check cell**. Then your turn → recap → appendix.

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/jupyter lab
```

## Rebuild / verify

`build_notebooks.py` is the single source for all notebooks:

```bash
python build_notebooks.py --run    # writes solution + starter notebooks and executes every solution
```
