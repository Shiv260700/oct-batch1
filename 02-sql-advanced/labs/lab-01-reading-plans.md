# Lab 01 — Reading an Execution Plan

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab01.sql`

## The story

- Customer **`u1000@bank`** calls support: *"Show me my payments."*
- The support screen is slow.
- **Your job:** find out *what PostgreSQL is doing*, before trying to fix anything.

## You will be able to

- Use `EXPLAIN` and `EXPLAIN (ANALYZE, BUFFERS)`
- Read every number on a plan line
- Read a plan tree **bottom-up**
- Tell a **Seq Scan** from an **Index Scan** and a **Bitmap Scan**
- Measure an improvement in **pages** and **milliseconds**

## How every step works

1. ❓ **Question:** what we want to know
2. 🤔 **Predict:** write your guess first
3. ▶️ **Run:** the SQL (also in `sql/lab01.sql`)
4. 👀 **See:** real output, with what to look at
5. 📌 **Remember:** one rule to keep

> Your milliseconds will differ from the trainer's (different laptops). **Rows, pages and plan shapes will match.**

---

## Step 0 — Clean start

▶️ **Run**

```sql
\i sql/reset.sql
SET max_parallel_workers_per_gather = 0;
```

- `reset.sql` removes indexes from earlier practice.
- The `SET` turns off parallel query **for now**, so the first plans are simple. It comes back in Step 9.

---

## Step 1 — How big is the table?

❓ How much data must PostgreSQL search to find one customer's payments?

▶️ **Run**

```sql
SELECT count(*) AS total_rows FROM transactions;

SELECT relpages AS pages_8kb,
       pg_size_pretty(pg_relation_size('transactions')) AS table_size,
       round(reltuples / relpages) AS rows_per_page
FROM pg_class
WHERE relname = 'transactions';
```

👀 **See**

```text
 total_rows        pages_8kb | table_size | rows_per_page
------------      -----------+------------+---------------
    1000000            12606 | 98 MB      |            79
```

- 1,000,000 rows live in **12,606 pages**.
- Keep **12,606** in mind. You will see it again.

📌 **Remember:** PostgreSQL reads pages, not rows. Pages read = work done.

---

## Step 2 — `EXPLAIN`: the plan only

❓ How *will* PostgreSQL find `u1000@bank`'s payments?

🤔 **Predict:** will it read the whole table? (There is no index on `payer_account` yet.)

▶️ **Run**

```sql
EXPLAIN
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';
```

👀 **See**

```text
 Seq Scan on transactions  (cost=0.00..25106.00 rows=98 width=68)
   Filter: (payer_account = 'u1000@bank'::text)
```

| Part | Meaning |
|---|---|
| `Seq Scan` | Read **every page**, top to bottom |
| `Filter:` | Check each row: keep it or throw it away |
| `cost=0.00..25106.00` | Estimated effort: *first row .. all rows*. **Not milliseconds.** |
| `rows=98` | Planner's **guess**: about 98 rows will match |
| `width=68` | Average row size in bytes |

- `EXPLAIN` alone does **not** run the query. It only shows the plan.

📌 **Remember:** `cost` is a points score for comparing plans, not time.

---

## Step 3 — Where does the cost come from?

❓ Why exactly 25,106?

▶️ **Run**

```sql
SHOW seq_page_cost;      -- 1
SHOW cpu_tuple_cost;     -- 0.01
SHOW cpu_operator_cost;  -- 0.0025

SELECT 12606 * 1.0 + 1000000 * 0.01 + 1000000 * 0.0025 AS total_cost;
```

👀 **See:** `25106.0000`, the same number as the plan.

| Work | Count | Price | Points |
|---|---|---|---|
| Read a page | 12,606 | 1.0 | 12,606 |
| Handle a row | 1,000,000 | 0.01 | 10,000 |
| Check `payer_account = ...` | 1,000,000 | 0.0025 | 2,500 |
| **Total** | | | **25,106** |

📌 **Remember:** the planner prices every possible plan this way and picks the **cheapest**.

---

## Step 4 — `EXPLAIN ANALYZE`: run and measure

❓ How long does it *really* take? Was the guess of 98 rows right?

▶️ **Run**

```sql
EXPLAIN ANALYZE
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';
```

👀 **See**

```text
 Seq Scan on transactions  (cost=0.00..25106.00 rows=98 width=68)
                           (actual time=0.244..35.303 rows=103 loops=1)
   Filter: (payer_account = 'u1000@bank'::text)
   Rows Removed by Filter: 999897
 Planning Time: 0.010 ms
 Execution Time: 35.311 ms
```

| Part | Meaning |
|---|---|
| `actual time=0.244..35.303` | **Real** milliseconds: first row .. last row |
| `rows=103` | **Real** rows returned (guess was 98: a good guess) |
| `loops=1` | This step ran once |
| `Rows Removed by Filter: 999897` | Rows read and **thrown away** |
| `Execution Time` | Total real time |

- **103 kept, 999,897 thrown away**: 99.99% of the work was wasted.

📌 **Remember:** a big `Rows Removed by Filter` next to a small `rows=` is the #1 sign of a missing index.

---

## Step 5 — `BUFFERS`: count the pages

❓ How many pages did it read?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';
```

👀 **See**

```text
 Seq Scan on transactions  (... actual time=0.304..36.559 rows=103 loops=1)
   Filter: (payer_account = 'u1000@bank'::text)
   Rows Removed by Filter: 999897
   Buffers: shared hit=12606
 Execution Time: 36.569 ms
```

- `shared hit=12606` = **every page of the table** (see Step 1).
- `hit` = page was already in PostgreSQL's memory (cache).
- `read` = page had to be fetched into memory (from disk or the OS cache).

📌 **Remember:** always use `EXPLAIN (ANALYZE, BUFFERS)`. Time changes from run to run; **pages don't**.

---

## Step 6 — A plan with 3 nodes: read it bottom-up

❓ How many FAILED payments are there per channel?

🤔 **Predict:** which step happens first: scan, group or sort?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT channel, count(*) AS failed
FROM transactions
WHERE status = 'FAILED'
GROUP BY channel
ORDER BY failed DESC;
```

👀 **See** (trimmed)

```text
 Sort  (... actual time=46.105..46.106 rows=3 loops=1)                 ③ sort 3 rows
   Sort Key: (count(*)) DESC
   ->  HashAggregate  (... actual time=46.101..46.101 rows=3 loops=1)  ② group into 3
         Group Key: channel
         ->  Seq Scan on transactions  (... rows=48998 loops=1)       ① read + filter
               Filter: (status = 'FAILED'::text)
               Rows Removed by Filter: 951002
 Execution Time: 46.117 ms
```

- Read from the **most indented line upward**:
  - ① **Seq Scan** reads 1M rows → keeps **48,998** FAILED rows
  - ② **HashAggregate** groups them → **3** rows (APP, UPI_QR, WEB)
  - ③ **Sort** orders the 3 rows → result
- `->` means "feeds into the line above".
- A parent's time **includes** its children. Don't add times together.

📌 **Remember:** a plan is a tree. Data flows **up** from the most indented node.

---

## Step 7 — Your first Index Scan

❓ Find payment number 500,000. Will it read all 12,606 pages?

🤔 **Predict:** `txn_id` is the **primary key**. Does it have an index?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE txn_id = 500000;
```

👀 **See**

```text
 Index Scan using transactions_pkey on transactions
        (cost=0.42..8.44 rows=1 width=68) (actual time=0.009..0.009 rows=1 loops=1)
   Index Cond: (txn_id = 500000)
   Buffers: shared hit=7
 Execution Time: 0.013 ms
```

- Every primary key gets an index **automatically** (`transactions_pkey`).
- `Index Cond:` means the index found the row directly. There is no `Filter`.
- **7 pages instead of 12,606.** Execution time 0.013 ms instead of 36 ms.

📌 **Remember:** `Index Cond` = the index did the searching. `Filter` = rows were checked one by one.

---

## Step 8 — Add an index for our story

❓ Will an index on `payer_account` fix customer `u1000@bank`'s slow screen?

▶️ **Run**

```sql
CREATE INDEX idx_txn_payer ON transactions (payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';
```

👀 **See**

```text
 Bitmap Heap Scan on transactions  (... actual time=0.023..0.128 rows=103 loops=1)
   Recheck Cond: (payer_account = 'u1000@bank'::text)
   Heap Blocks: exact=103
   Buffers: shared hit=103 read=3
   ->  Bitmap Index Scan on idx_txn_payer  (... rows=103 loops=1)
         Index Cond: (payer_account = 'u1000@bank'::text)
         Buffers: shared read=3
 Execution Time: 0.140 ms
```

- Two steps (read bottom-up):
  - **Bitmap Index Scan:** search the index → list of **103 row locations** (3 index pages)
  - **Bitmap Heap Scan:** visit those **103 table pages**, in page order
- Why "Bitmap"? The 103 rows sit on 103 different pages. PostgreSQL first collects all locations, then reads each page **once, in order**.

| | Before | After |
|---|---|---|
| Plan | Seq Scan | Bitmap Index Scan → Bitmap Heap Scan |
| Pages | 12,606 | 106 |
| Rows thrown away | 999,897 | 0 |
| Time | ~36 ms | ~0.1 ms |

📌 **Remember:** the index helped because we wanted **very few** rows (103 out of 1,000,000).

---

## Step 9 — Parallel query

❓ What happens when several CPU workers share one scan?

▶️ **Run**

```sql
RESET max_parallel_workers_per_gather;   -- back to default: 2 workers

EXPLAIN (ANALYZE, BUFFERS)
SELECT channel, count(*) AS failed
FROM transactions
WHERE status = 'FAILED'
GROUP BY channel
ORDER BY failed DESC;
```

👀 **See** (trimmed)

```text
 Sort  (... rows=3 loops=1)
   ->  Finalize GroupAggregate  (... rows=3 loops=1)
         ->  Gather Merge  (... rows=9 loops=1)
               Workers Launched: 2
               ->  Sort  (... rows=3 loops=3)
                     ->  Partial HashAggregate  (... rows=3 loops=3)
                           ->  Parallel Seq Scan on transactions  (... rows=16333 loops=3)
                                 Rows Removed by Filter: 317001
 Execution Time: 19.843 ms
```

- **3 workers** (2 helpers + the main process) each scan about ⅓ of the table.
- `loops=3`: the numbers are **per worker**. Total rows = 16,333 × 3 = **48,999 ≈ 48,998**.
- Each worker groups its own share → **Gather Merge** collects 3 × 3 = 9 rows → **Finalize** combines them into 3.
- Time dropped from ~46 ms to ~20 ms. **Pages read are the same (12,606).**

📌 **Remember:** with `loops=N`, multiply `rows` by N. Parallel query shares the work; it does **not** reduce it.

---

## Step 10 — Safety: `EXPLAIN ANALYZE` really runs the statement

▶️ **Run**

```sql
BEGIN;
EXPLAIN ANALYZE UPDATE transactions SET status = 'FAILED' WHERE txn_id = 1;
SELECT txn_id, status FROM transactions WHERE txn_id = 1;   -- FAILED: it changed!
ROLLBACK;
SELECT txn_id, status FROM transactions WHERE txn_id = 1;   -- SUCCESS again
```

- `EXPLAIN ANALYZE` on `UPDATE` / `DELETE` / `INSERT` **changes data**.
- Always wrap it in `BEGIN; ... ROLLBACK;`.

📌 **Remember:** `EXPLAIN` = plan only (safe). `EXPLAIN ANALYZE` = really runs it.

---

## Lab 01 summary

| You saw | It means |
|---|---|
| `Seq Scan` + big `Rows Removed by Filter` | Reading everything to find little: index candidate |
| `Index Scan` + `Index Cond` | Index found the rows directly |
| `Bitmap Index Scan` → `Bitmap Heap Scan` | Index finds locations, then table pages are read in order |
| `cost=` | Planner's estimate in points (not ms) |
| `rows=` vs `actual ... rows=` | Guess vs reality |
| `Buffers: shared hit/read` | Pages touched: the best measure of work |
| `loops=N` | Multiply rows by N |

### How to read any plan: 5 questions

1. Which node is **most indented**? Start there.
2. How does it **access** the table: Seq Scan or an index?
3. How many rows are **thrown away** (`Rows Removed by Filter`)?
4. Is the **estimate** (`rows=`) close to the **actual** rows?
5. How many **pages** (`Buffers`)?

---

## Try it yourself

- **T1.** Run `EXPLAIN (ANALYZE, BUFFERS)` for the busy payer `'u42@bank'`.
  - How many rows? How many `Heap Blocks`? Faster or slower than `u1000@bank`? Why?
- **T2.** Estimate vs actual:
  ```sql
  EXPLAIN ANALYZE
  SELECT count(*) FROM transactions
  WHERE status = 'FAILED' AND channel = 'WEB';
  ```
  - Compare the estimated `rows=` with the actual `rows=`. How far off is it?
- **T3.** In Step 6, which node handles the **most** rows? Which the **fewest**?
- **T4.** Run `EXPLAIN` for `SELECT * FROM merchants WHERE merchant_account = 'merchant7';`
  - Which index is used? Why does it already exist?

---

## Common mistakes

- ❌ Reading `cost` as milliseconds → it is a points score
- ❌ Reading the plan top-down → start from the **most indented** node
- ❌ Adding node times together → parent time already includes children
- ❌ Forgetting `loops=3` in parallel plans → multiply rows by loops
- ❌ Comparing one timing run → run twice; compare **pages**, not just ms
- ❌ `EXPLAIN ANALYZE DELETE ...` without `BEGIN/ROLLBACK` → data is gone

---

## Quick quiz

1. Does `EXPLAIN` (without `ANALYZE`) run the query?
2. A plan says `rows=98`, and actual says `rows=103`. Which one is the guess?
3. `Buffers: shared hit=12606` on a 12,606-page table. What does that tell you?
4. In a plan, which line runs first: the top line or the most indented line?
5. A Parallel Seq Scan shows `rows=500 loops=3`. How many rows in total?

**Next:** Lab 02 — Index Design (which index, which columns, which order)
