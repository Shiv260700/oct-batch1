# Labs 2 · Real projects, best practices

Each lab is a complete project, done the way it is done at work.
- 🧠 cells: write your guess first
- ✓ cells: the notebook proves the result (it asserts every claim)

| Lab | Project | Practises |
|---|---|---|
| `01-prediction` | Predict 1,000 students’ final marks | look first · locked test set · baseline · leak hunt · pipeline · cross-validation · test with a range · read mistakes · explain · save · input checks |
| `02-classification` | Which of 3,000 students will drop out? (11% yes) | stratified splits · accuracy lies · leak hunt · PR-AUC / ROC-AUC / Brier · calibration · cut-off from costs · capacity rule · test with a range · save with cut-off |
| `03-neural-network` | Read handwritten digits (Keras) | scale + 3-way split · baseline · learning curves · overfitting · early stopping, dropout · CNN · test with a range · confidence rule · save/reload |
| `04-text-classification` | Sort forum posts into 6 topics | leak in text (headers) · time-ordered test · empty texts · tuned TF-IDF baseline · top words · pretrained embeddings · few labels · mistakes by length · route to a person · save |

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python make_data.py      # creates data/students.csv and data/dropout.csv (lab 3: built-in digits; lab 4 downloads 20 Newsgroups ≈ 14 MB and MiniLM ≈ 90 MB on first run)
jupyter lab
```

## Files
- `make_data.py`: makes both datasets (synthetic, with missing values, outliers and a leaking column on purpose)
- `build.py`: writes every notebook and its `starter/` version; `python build.py --run` executes and checks them
- `starter/`: versions with TODO cells for students

## Teacher's numbers
**01-prediction**
- Baseline MAE 9.15 · `grade` alone 3.48 (leak)
- 5-fold CV: linear 4.72 · linear + sleep² 4.02 · **Huber + sleep² 3.90** · random forest 4.93 · boosting 4.92
- Locked test: **MAE 3.63 (range 3.05–4.29)** vs baseline 8.16
- Worst misses = students ill on exam day · Asha 85.1 (truth 85.7) · messy input 63.7, flagged

**02-classification**
- Dropout rate 10.9% · “nobody drops out”: accuracy 89.1%, recall 0 · exit survey alone PR-AUC 0.91 (leak)
- 5-fold CV: **logistic PR-AUC 0.53, ROC-AUC 0.88, Brier 0.069** · balanced 0.53 / Brier 0.139 · random forest 0.45 · boosting 0.40
- Cost 10:1 → cut-off 0.12, recall 29% → 78% · top-100 calls catch 64 vs ≈ 11 at random
- Locked test: **caught 62 of 81 (77%, range 67–86%)** vs 37% at 0.5 · 187 calls of 750

**03-neural-network** (1,797 digit images, 8×8)
- Logistic regression 96.7% (validation)
- Small dense 97.5% · big dense, no protection: val loss 0.099 at epoch 15 → 0.159 at epoch 200, train 100% (overfitting)
- Early stopping: stops at 30 of 300 epochs · + dropout: val loss 0.084, 98.3%
- **CNN: 98.6%, val loss 0.044**, 43k weights (vs 301k for big dense)
- Locked test: **98.3% (range 96.9–99.4%)**, 6 mistakes of 360
- Confidence ≥ 0.9: 3.1% sent to a person, 99.7% accurate on the rest, 5 of 6 mistakes caught

**04-text-classification** (20 Newsgroups, 6 topics; test posts are later in time)
- Raw posts (with headers, signatures): CV 97.3%, test 95.6% → cleaned: 88.1%, 84.8% (the leak)
- Empty after cleaning: 106 train, 75 test (dropped from training only)
- Tuned TF-IDF + logistic: CV 89.5%, **test 83.9%** · MiniLM + logistic: CV 90.0%, **test 87.6%**
- 10 labels per topic: MiniLM 79% vs TF-IDF 51% · 100 per topic: 87% vs 79%
- By length: empty 12%, 31–100 words 92%, 100+ words 94%
- Rule (< 5 words or p < 0.5 → person): 14.2% to a person, **95.8%** on the rest
