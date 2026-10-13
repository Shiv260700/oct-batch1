# Lab 02 — Index Design

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab02.sql`

## The story

- Lab 01 fixed the support screen for **`u1000@bank`** with one index.
- Now new requests arrive:
  - "Show the customer's **latest 10** payments"
  - "How many payments on **15 March**?"
  - "Find a customer by **name**, any case"
  - "Show the **failed payments** queue"
- **Your job:** pick the *right* index for each question, and prove it with the plan.

## You will be able to

- Predict when PostgreSQL **uses** an index and when it **ignores** it
- Design a **composite** index (column order matters)
- Write **index-friendly** (SARGable) filters
- Use **expression**, **partial**, **covering** and **BRIN** indexes
- Measure what indexes **cost**: space and slower writes

## How every step works

1. ❓ **Question:** 2. 🤔 **Predict:** 3. ▶️ **Run:** 4. 👀 **See:** 5. 📌 **Remember:**

> Milliseconds differ per laptop. Actual rows, plan shapes and pages match the trainer's.
> Estimates (`rows=` without "actual") can move slightly after each `ANALYZE`. That is normal.

---

## Step 0 — Clean start

▶️ **Run**

```sql
\i sql/reset.sql
SET max_parallel_workers_per_gather = 0;
```

- Removes indexes from Lab 01.
- Parallel query stays **off for this whole lab**, so plans stay short and easy to compare.

---

## Step 1 — Selectivity: how many rows does a filter keep?

❓ Which filters are "narrow" and which are "wide"?

▶️ **Run**

```sql
SELECT status, count(*) AS payments,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_table
FROM transactions
GROUP BY status
ORDER BY payments DESC;

SELECT payer_account, count(*) AS payments
FROM transactions
WHERE payer_account IN ('u1000@bank', 'u42@bank')
GROUP BY payer_account;
```

👀 **See**

| Filter | Rows | % of table |
|---|---|---|
| `payer_account = 'u1000@bank'` | 103 | 0.01% |
| `status = 'PENDING'` | 9,979 | 1% |
| `payer_account = 'u42@bank'` | 10,216 | 1% |
| `status = 'FAILED'` | 48,998 | 4.9% |
| `status = 'SUCCESS'` | 941,023 | **94.1%** |

- **Selectivity** = fraction of rows a filter keeps.
- Small fraction = **selective** = good index candidate.

📌 **Remember:** an index pays off when it lets PostgreSQL **skip most pages**.

---

## Step 2 — Same index, different number of rows

❓ The payer index made `u1000@bank` fast. Is it equally good for the busy payer `u42@bank`?

🤔 **Predict:** how many table pages for 103 rows? For 10,216 rows?

▶️ **Run**

```sql
CREATE INDEX idx_txn_payer ON transactions (payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE payer_account = 'u1000@bank';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE payer_account = 'u42@bank';
```

👀 **See** (trimmed)

```text
 Bitmap Heap Scan on transactions  (... actual time=0.021..0.143 rows=103 loops=1)
   Heap Blocks: exact=103
 Execution Time: 0.154 ms

 Bitmap Heap Scan on transactions  (... actual time=1.116..12.718 rows=10216 loops=1)
   Heap Blocks: exact=7017
 Execution Time: 13.020 ms
```

- `u1000@bank`: **103** table pages of 12,606.
- `u42@bank`: **7,017** table pages: more than **half the table**.
- Same index, same query shape, very different work.

📌 **Remember:** an index is only as good as the number of rows it lets you **avoid**.

---

## Step 3 — When the planner ignores an index

❓ We index `status`. Will `WHERE status = 'SUCCESS'` use it?

🤔 **Predict:** `PENDING` is 1% of rows; `SUCCESS` is 94%.

▶️ **Run**

```sql
CREATE INDEX idx_txn_status ON transactions (status);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'PENDING';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'SUCCESS';
```

👀 **See** (trimmed)

```text
 Index Scan using idx_txn_status on transactions  (... rows=9979 loops=1)
   Index Cond: (status = 'PENDING'::text)

 Seq Scan on transactions  (... rows=941023 loops=1)
   Filter: (status = 'SUCCESS'::text)
   Rows Removed by Filter: 58977
   Buffers: shared hit=12606
```

- `PENDING` (1%) → **Index Scan**.
- `SUCCESS` (94%) → **Seq Scan**: the index is **ignored**. That is correct, not a bug.

▶️ **Prove it:** force the index (learning only)

```sql
BEGIN;
SET LOCAL enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'SUCCESS';
ROLLBACK;
```

```text
 Bitmap Heap Scan on transactions  (... rows=941023 loops=1)
   Heap Blocks: exact=12606
   Buffers: shared hit=12609 read=792
```

- Forced plan still reads **all 12,606 table pages** **plus 792 index pages**.
- More work, no gain. The planner was right.

📌 **Remember:** when a filter keeps most of the table, reading the table directly is cheapest. **Low selectivity → Seq Scan**.

---

## Step 4 — Composite index: "latest 10 payments"

❓ Show the latest 10 payments of the busy payer `u42@bank`.

▶️ **Run** with only the single-column payer index

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount, status
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

👀 **See** (trimmed)

```text
 Limit  (... rows=10 loops=1)
   ->  Sort  (... rows=10 loops=1)
         Sort Key: txn_ts DESC
         Sort Method: top-N heapsort  Memory: 26kB
         ->  Bitmap Heap Scan on transactions  (... rows=10216 loops=1)
               Heap Blocks: exact=7017
 Execution Time: 5.977 ms
```

- Fetch **all 10,216** rows → sort them → keep **10**.

▶️ **Run** with a composite index: equality column first, then the `ORDER BY` column

```sql
CREATE INDEX idx_txn_payer_ts ON transactions (payer_account, txn_ts DESC);

-- run the same EXPLAIN again
```

👀 **See**

```text
 Limit  (... actual time=0.021..0.028 rows=10 loops=1)
   ->  Index Scan using idx_txn_payer_ts on transactions  (... rows=10 loops=1)
         Index Cond: (payer_account = 'u42@bank'::text)
         Buffers: shared hit=10 read=3
 Execution Time: 0.035 ms
```

- **No Sort node.** The index already keeps each payer's rows newest-first.
- Reads the first 10 entries and **stops**: 13 pages instead of 7,029.

📌 **Remember:** for `WHERE a = ? ORDER BY b LIMIT n`, index `(a, b)`. Then the index does the sorting.

---

## Step 5 — Column order matters

❓ Would `(txn_ts, payer_account)` work just as well?

🤔 **Predict:** think of a **phone directory** sorted by *surname, then first name*. Can it find "everyone named Ravi" quickly?

▶️ **Run** (inside a transaction so we can undo)

```sql
BEGIN;
DROP INDEX idx_txn_payer_ts;
DROP INDEX idx_txn_payer;
CREATE INDEX idx_txn_ts_payer ON transactions (txn_ts DESC, payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount, status
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC
LIMIT 10;
ROLLBACK;
```

👀 **See**

```text
 Limit  (... actual time=0.055..3.606 rows=10 loops=1)
   ->  Index Scan using idx_txn_ts_payer on transactions  (... rows=10 loops=1)
         Index Cond: (payer_account = 'u1000@bank'::text)
         Buffers: shared hit=10 read=651
 Execution Time: 3.613 ms
```

| Index | Pages | Time |
|---|---|---|
| `(payer_account, txn_ts DESC)` | 13 | ~0.03 ms |
| `(txn_ts DESC, payer_account)` | 661 | ~3.6 ms |

- Wrong order: PostgreSQL walks the index **from newest to oldest** and checks every entry's payer.
- Right order: jumps straight to `u1000@bank`'s section.

📌 **Remember:** put the **equality** column (`=`) **first**, then the range / `ORDER BY` column.

---

## Step 6 — Don't wrap the indexed column (SARGable filters)

❓ How many payments on **15 March 2026**?

▶️ **Run**

```sql
CREATE INDEX idx_txn_ts ON transactions (txn_ts);

-- A: cast the column
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts::date = DATE '2026-03-15';

-- B: half-open range on the bare column
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15'
  AND txn_ts <  TIMESTAMP '2026-03-16';
```

👀 **See** (trimmed)

```text
 A:  ->  Seq Scan on transactions  (... rows=11186 loops=1)
           Filter: ((txn_ts)::date = '2026-03-15'::date)
           Rows Removed by Filter: 988814
           Buffers: shared hit=12606
     Execution Time: 55.187 ms

 B:  ->  Index Only Scan using idx_txn_ts on transactions  (... rows=11186 loops=1)
           Index Cond: ((txn_ts >= '2026-03-15 00:00:00') AND (txn_ts < '2026-03-16 00:00:00'))
           Heap Fetches: 0
           Buffers: shared hit=1 read=33
     Execution Time: 1.085 ms
```

- Same answer: **11,186** payments.
- A: index stores `txn_ts`, but we asked about `txn_ts::date` → index **can't be used** → 12,606 pages.
- B: compares the bare column → **Index Cond** → 34 pages.
- Half-open `>= start AND < next day` catches every second of the day, including 23:59:59.

📌 **Remember:** keep the indexed column **bare** on one side. Move the maths to the other side.

---

## Step 7 — Expression index: search by name, any case

❓ Support types "RAVI KUMAR", "ravi kumar" or "Ravi Kumar". Find the customer.

▶️ **Run**

```sql
CREATE INDEX idx_acc_name ON accounts (holder_name);

EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name, city
FROM accounts
WHERE lower(holder_name) = 'ravi kumar';
```

👀 **See**

```text
 Seq Scan on accounts  (... rows=25 loops=1)
   Filter: (lower(holder_name) = 'ravi kumar'::text)
   Rows Removed by Filter: 9975
```

- The plain index on `holder_name` is **not used**: it stores "Ravi Kumar", not "ravi kumar".

▶️ **Run:** index the **expression** itself

```sql
CREATE INDEX idx_acc_name_lower ON accounts (lower(holder_name));
-- run the same EXPLAIN again
```

```text
 Bitmap Heap Scan on accounts  (... rows=25 loops=1)
   ->  Bitmap Index Scan on idx_acc_name_lower  (... rows=25 loops=1)
         Index Cond: (lower(holder_name) = 'ravi kumar'::text)
```

- 25 matching customers, found through the index.

📌 **Remember:** if the query must use a function, index **exactly that expression**.

---

## Step 8 — Partial index: the failed-payments queue

❓ Ops screen: "latest 20 **FAILED** payments". Do we need to index all 1,000,000 rows?

▶️ **Run**

```sql
CREATE INDEX idx_txn_failed_ts ON transactions (txn_ts DESC)
WHERE status = 'FAILED';

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount, txn_ts
FROM transactions
WHERE status = 'FAILED'
ORDER BY txn_ts DESC
LIMIT 20;

SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexrelname IN ('idx_txn_ts', 'idx_txn_failed_ts');
```

👀 **See**

```text
 Limit  (... rows=20 loops=1)
   ->  Index Scan using idx_txn_failed_ts on transactions  (... rows=20 loops=1)
         Buffers: shared hit=5 read=2

    index_name     |  size
 idx_txn_ts        | 21 MB
 idx_txn_failed_ts | 1088 kB
```

- Before this index, the plan walked `idx_txn_ts` backwards and **skipped 298 SUCCESS rows** (`Rows Removed by Filter`).
- Partial index holds **only FAILED rows**: no skipping, **20× smaller** (1 MB vs 21 MB).
- The query's `WHERE` must **match** the index's `WHERE` (`status = 'FAILED'`).

📌 **Remember:** if a screen always looks at the same small slice, index **only that slice**.

---

## Step 9 — Covering index: answer from the index alone

❓ The mobile app shows only **date and amount** for `u1000@bank`.

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC;
```

```text
 Sort  (... rows=103 loops=1)
   ->  Bitmap Heap Scan on transactions  (... rows=103 loops=1)
         Heap Blocks: exact=103
```

- `amount` is not in any index → visit 103 table pages.

▶️ **Run:** add `amount` as a passenger with `INCLUDE`

```sql
CREATE INDEX idx_txn_payer_ts_amt ON transactions (payer_account, txn_ts DESC)
INCLUDE (amount);
-- run the same EXPLAIN again
```

```text
 Index Only Scan using idx_txn_payer_ts_amt on transactions  (... rows=103 loops=1)
   Index Cond: (payer_account = 'u1000@bank'::text)
   Heap Fetches: 0
   Buffers: shared hit=1 read=3
```

- **Index Only Scan**: every column needed is inside the index.
- `Heap Fetches: 0`: the table was not touched at all. 4 pages instead of 106.

📌 **Remember:** `INCLUDE` columns ride along in the index so the table visit can be skipped.

---

## Step 10 — Why `Heap Fetches` can appear

❓ Can an Index Only Scan still visit the table?

▶️ **Run**

```sql
BEGIN;
UPDATE transactions SET amount = amount WHERE payer_account = 'u1000@bank';
ROLLBACK;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount FROM transactions
WHERE payer_account = 'u1000@bank' ORDER BY txn_ts DESC;

VACUUM transactions;

-- run the same EXPLAIN again
```

👀 **See**

```text
 After UPDATE + ROLLBACK:   Heap Fetches: 206    Buffers: shared hit=211
 After VACUUM:              Heap Fetches: 0      Buffers: shared hit=5
```

- The index cannot tell if a row is **visible** (committed, not deleted).
- PostgreSQL keeps a **visibility map**: one flag per page, "every row here is visible".
- Our update + rollback cleared those flags → each index entry is checked in the table.
- `VACUUM` cleans up and sets the flags again → back to 0.

📌 **Remember:** Index Only Scans work best on tables that are **vacuumed** (autovacuum normally does this).

---

## Step 11 — BRIN: a tiny index for time-ordered data

❓ Payments arrive in time order. Is there a cheaper index than a 21 MB B-tree?

▶️ **Run**

```sql
SELECT attname, correlation FROM pg_stats
WHERE tablename = 'transactions' AND attname IN ('txn_ts', 'payer_account');

CREATE INDEX idx_txn_ts_brin ON transactions USING brin (txn_ts);

SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexrelname IN ('idx_txn_ts', 'idx_txn_ts_brin');

BEGIN;
DROP INDEX idx_txn_ts;          -- hide the B-tree for a moment
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15' AND txn_ts < TIMESTAMP '2026-03-16';
ROLLBACK;
```

👀 **See**

```text
 txn_ts        | 1          ← perfectly in time order on disk
 payer_account | -0.001     ← random order

 idx_txn_ts      | 21 MB
 idx_txn_ts_brin | 24 kB

 ->  Bitmap Heap Scan on transactions  (... rows=11186 loops=1)
       Rows Removed by Index Recheck: 9129
       Heap Blocks: lossy=256
       ->  Bitmap Index Scan on idx_txn_ts_brin
```

- BRIN stores only **min/max per block of pages**: "pages 9,000–9,127 hold 14–15 March".
- **~900× smaller** than the B-tree (24 kB vs 21 MB).
- It points to page ranges, not rows → **lossy**: 256 pages read, 9,129 extra rows rechecked.
- Still far better than 12,606 pages. Only works because `txn_ts` follows the physical order (correlation 1).

📌 **Remember:** BRIN = tiny index for **huge, append-only** tables filtered by time. Useless on random-order columns.

---

## Step 12 — Indexes are not free

❓ We created 7 indexes. What did they cost?

▶️ **Run:** space

```sql
SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE relname = 'transactions'
ORDER BY pg_relation_size(indexrelid) DESC;

SELECT pg_size_pretty(pg_relation_size('transactions')) AS table_size,
       pg_size_pretty(pg_indexes_size('transactions'))  AS all_indexes_size;
```

👀 **See**

```text
      index_name      |  size
 idx_txn_payer_ts_amt | 49 MB
 idx_txn_payer_ts     | 39 MB
 transactions_pkey    | 21 MB
 idx_txn_ts           | 21 MB
 idx_txn_payer        | 7048 kB
 idx_txn_status       | 6792 kB
 idx_txn_failed_ts    | 1088 kB
 idx_txn_ts_brin      | 24 kB

 table_size | all_indexes_size
 98 MB      | 145 MB          ← indexes are bigger than the table!
```

- `times_used` (`idx_scan`) shows which indexes are actually used. Unused for weeks = candidate to drop.
- Notice the overlap: `idx_txn_payer`, `idx_txn_payer_ts`, `idx_txn_payer_ts_amt` all start with `payer_account`.

▶️ **Run:** write cost. Load 50,000 rows into two empty copies of the table

```sql
CREATE TABLE load_plain   (LIKE transactions);                     -- no indexes
CREATE TABLE load_indexed (LIKE transactions INCLUDING INDEXES);   -- same 8 indexes

EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO load_plain   SELECT * FROM transactions WHERE txn_id <= 50000;

EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO load_indexed SELECT * FROM transactions WHERE txn_id <= 50000;

DROP TABLE load_plain;
DROP TABLE load_indexed;
```

👀 **See**

| Copy | Insert 50,000 rows | Pages dirtied | Total size |
|---|---|---|---|
| `load_plain` (no indexes) | ~21 ms | 632 | 5 MB |
| `load_indexed` (8 indexes) | ~355 ms | 1,818 | 14 MB |

- Every `INSERT` must also update **every index**. **~15× slower** here.
- `UPDATE` and `DELETE` pay the same price.

📌 **Remember:** every index speeds up some reads and slows **every** write. Keep only indexes that earn their place.

---

## Lab 02 summary

| Question type | Index | Example |
|---|---|---|
| Find a few rows by value | B-tree on the column | `(payer_account)` |
| Filter keeps most rows | **No index**: Seq Scan wins | `status = 'SUCCESS'` |
| `WHERE a = ? ORDER BY b LIMIT n` | Composite `(a, b)` | `(payer_account, txn_ts DESC)` |
| Filter on a function | Expression index **or** rewrite | `lower(holder_name)`, date range |
| Always the same small slice | Partial index | `WHERE status = 'FAILED'` |
| Need few columns, no table visit | Covering `INCLUDE` | `INCLUDE (amount)` |
| Huge, time-ordered table | BRIN | `USING brin (txn_ts)` |

### Index design checklist

1. Which **query** needs it? (No query → no index.)
2. How **selective** is the filter?
3. **Equality columns first**, then range / `ORDER BY`.
4. Is the column **bare** in the `WHERE`?
5. Did the plan **change**, and did pages go **down**?
6. Can an **existing** index be extended instead of adding a new one?

---

## Try it yourself

- **T1.** Ops asks: "top 5 **biggest** payments of `u1000@bank`".
  - Design an index so the plan has **no Sort** node. Prove it with `EXPLAIN (ANALYZE, BUFFERS)`.
- **T2.** Is `WHERE channel = 'WEB'` (15% of rows) a good index candidate?
  - Create the index, run the plan, count the table pages it reads.
- **T3.** Rewrite to be index-friendly (index on `txn_ts` exists):
  ```sql
  SELECT count(*) FROM transactions
  WHERE date_trunc('month', txn_ts) = TIMESTAMP '2026-02-01';
  ```
- **T4.** Make this fast with a **partial** index, and check its size:
  ```sql
  SELECT * FROM transactions
  WHERE status = 'PENDING' AND payee_account IS NULL;
  ```

---

## Common mistakes

- ❌ "Index every column in the `WHERE`" → index for **queries**, not columns
- ❌ Indexing a column where one value is 94% of rows → Seq Scan wins anyway
- ❌ Composite index in the wrong order → equality first, then range / sort
- ❌ `WHERE txn_ts::date = ...`, `WHERE lower(x) = ...` without a matching index
- ❌ Partial index whose `WHERE` does not match the query's `WHERE`
- ❌ Forgetting the write cost: 8 indexes = ~15× slower inserts here
- ❌ Keeping three overlapping indexes "just in case"

---

## Quick quiz

1. A filter keeps 94% of rows and an index exists. Which scan do you expect?
2. Query: `WHERE payer_account = ? ORDER BY txn_ts DESC LIMIT 10`. Which index removes the Sort?
3. Why can't an index on `txn_ts` help `WHERE txn_ts::date = '2026-03-15'`?
4. What does `Heap Fetches: 0` in an Index Only Scan tell you?
5. BRIN is 24 kB, B-tree is 21 MB. Why not always use BRIN?

**Next:** Lab 03 — Joins (Nested Loop, Hash Join, Merge Join)
