# Lab 04 — Rewriting Queries for Performance

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab04.sql`

## The story

- The operations team has a **merchant dashboard**: payments per merchant, sales per category, latest payments, payment history pages.
- Every widget gives the **right answer**, but slowly.
- **Your job:** rewrite the SQL so it does **less work**, and **prove** the answer did not change.

## You will be able to

- Replace a **correlated subquery** with "group once, then join"
- **Pre-aggregate** before a join
- Control **CTEs** (`WITH`): inlined vs `MATERIALIZED`
- Solve **top-N per group** with `row_number()`, `DISTINCT ON` and `LATERAL`
- Replace deep **OFFSET** pagination with **keyset** pagination
- Fix a wrong row **estimate** with `CREATE STATISTICS`
- **Prove** two queries return the same rows (`EXCEPT ALL`)

## How every step works

1. ❓ **Question** · 2. 🤔 **Predict** · 3. ▶️ **Run** · 4. 👀 **See** · 5. 📌 **Remember**

> Your milliseconds will differ from the trainer's. **Rows, pages and plan shapes will match.**

---

## Step 0 — Clean start

▶️ **Run**

```sql
\i sql/reset.sql
SET max_parallel_workers_per_gather = 0;   -- shorter plans (parallel: see Lab 01)
SET jit = off;                             -- no JIT compiler notes in big plans
```

- Both `SET`s only make plans **easier to read**. They are not tuning tips.

---

## Step 1 — Correlated subquery: one count per merchant

❓ How many payments did each merchant receive?

🤔 **Predict:** the subquery is inside `SELECT`. How many times will it run?

▶️ **Run** (first 20 merchants only)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       (SELECT count(*)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m
ORDER BY m.merchant_account
LIMIT 20;
```

👀 **See** (trimmed)

```text
 Limit  (... actual time=41.841..826.988 rows=20 loops=1)
   Buffers: shared hit=190743 read=61380
   ->  Index Only Scan using merchants_pkey on merchants m  (... rows=20 loops=1)
         SubPlan 1
           ->  Aggregate  (... actual time=41.346..41.346 rows=1 loops=20)
                 ->  Seq Scan on transactions t  (... rows=1709 loops=20)
                       Filter: (payee_account = m.merchant_account)
                       Rows Removed by Filter: 998291
 Execution Time: 827.004 ms
```

- `SubPlan` + `loops=20` → the subquery ran **once per merchant**.
- Each run is a **full table scan** (~41 ms, 12,606 pages).
- 20 merchants → 20 × 12,606 = **~252,000 pages** → **827 ms**.

▶️ **Run** the full list, **plan only** (do not add `ANALYZE`)

```sql
EXPLAIN
SELECT m.merchant_account,
       (SELECT count(*) FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m;
```

```text
 Seq Scan on merchants m  (cost=0.00..50214620.00 rows=2000 width=20)
   SubPlan 1
     ->  Aggregate  (cost=25107.28..25107.29 rows=1 width=8)
           ->  Seq Scan on transactions t  (cost=0.00..25106.00 rows=512 width=0)
```

- Cost **50,214,620** = 2,000 merchants × 25,107 per scan.
- 2,000 × 41 ms ≈ **82 seconds**.

📌 **Remember:** `SubPlan` with a big `loops=` = the same work repeated row by row.

---

## Step 2 — Rewrite: group once, then join

❓ Can we count **all** merchants in **one** pass?

🤔 **Predict:** how many times will `transactions` be scanned now?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       COALESCE(c.payments, 0) AS payments
FROM merchants m
LEFT JOIN (SELECT payee_account, count(*) AS payments
           FROM transactions
           GROUP BY payee_account) c
       ON c.payee_account = m.merchant_account;
```

👀 **See** (trimmed)

```text
 Hash Left Join  (... actual time=161.693..162.034 rows=2000 loops=1)
   Hash Cond: (m.merchant_account = c.payee_account)
   ->  Seq Scan on merchants m  (... rows=2000 loops=1)
   ->  Hash  (... rows=1950 loops=1)
         ->  HashAggregate  (... rows=1951 loops=1)
               Group Key: transactions.payee_account
               ->  Seq Scan on transactions  (... rows=1000000 loops=1)
 Execution Time: 162.105 ms
```

- `transactions` scanned **once** (`loops=1`) → 1,951 groups (1,950 merchants + 1 NULL payee group).
- **All 2,000 merchants in 162 ms**, vs ~82 s.
- `LEFT JOIN` + `COALESCE(..., 0)` keeps the 50 merchants with **no** payments.

📌 **Remember:** don't ask the same question 2,000 times. Ask once, then look up the answers.

---

## Step 3 — Or: give the subquery an index

❓ Is the correlated subquery always bad?

▶️ **Run**

```sql
CREATE INDEX idx_txn_payee ON transactions (payee_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       (SELECT count(*) FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m;
```

👀 **See** (trimmed)

```text
 Seq Scan on merchants m  (... actual time=1.921..88.494 rows=2000 loops=1)
   SubPlan 1
     ->  Aggregate  (... actual time=0.044..0.044 rows=1 loops=2000)
           ->  Index Only Scan using idx_txn_payee on transactions t  (... rows=499 loops=2000)
                 Index Cond: (payee_account = m.merchant_account)
                 Heap Fetches: 0
 Execution Time: 88.582 ms
```

- Still 2,000 loops, but each loop is now an **index lookup** (0.044 ms), not a full scan.
- 2,000 merchants in **88 ms**.

| Version | Work | Time |
|---|---|---|
| Correlated, no index | 2,000 full scans | ~82 s (estimated) |
| Group once + join | 1 full scan | 162 ms |
| Correlated + index | 2,000 index lookups | 88 ms |

📌 **Remember:** repeated work is fine if each repeat is **cheap**. The problem is a repeated **full scan**.

---

## Step 4 — Prove the rewrite gives the same answer

❓ The rewrite is faster. Is it **correct**?

▶️ **Run**: the **equivalence template** (use it after every rewrite)

```sql
WITH a AS (     -- original
    SELECT m.merchant_account,
           (SELECT count(*) FROM transactions t
            WHERE t.payee_account = m.merchant_account) AS payments
    FROM merchants m
), b AS (       -- rewrite
    SELECT m.merchant_account, COALESCE(c.payments, 0) AS payments
    FROM merchants m
    LEFT JOIN (SELECT payee_account, count(*) AS payments
               FROM transactions GROUP BY payee_account) c
           ON c.payee_account = m.merchant_account
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_original,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_rewrite;
```

👀 **See**

```text
 only_in_original | only_in_rewrite
------------------+-----------------
                0 |               0
```

- `0 | 0` → exactly the same rows, including duplicates.
- Now change the rewrite to `JOIN` (instead of `LEFT JOIN`) and run it again (Step 4 in `sql/lab04.sql`):

```text
 only_in_original | only_in_rewrite
------------------+-----------------
               50 |               0
```

- **50 merchants vanished**: the ones with no payments. Faster, but **wrong**.
- Why `EXCEPT ALL` and not `EXCEPT`? `ALL` also catches a row that appears a different **number of times**.

📌 **Remember:** faster but different answer = **bug**. Always check both directions: `0 | 0`.

---

## Step 5 — Pre-aggregate before the join

❓ Sales per category: does it matter **when** we group?

🤔 **Predict:** join 1,000,000 payments to merchants, or shrink them first?

▶️ **Run**

```sql
-- 5a. Join first, then group
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;

-- 5b. Group by merchant first, then join
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, sum(s.payments) AS payments, sum(s.total) AS total
FROM (SELECT payee_account, count(*) AS payments, sum(amount) AS total
      FROM transactions
      GROUP BY payee_account) s
JOIN merchants m ON m.merchant_account = s.payee_account
GROUP BY m.category
ORDER BY total DESC;
```

👀 **See** (trimmed)

```text
-- 5a
   ->  HashAggregate  (... rows=6 loops=1)
         ->  Hash Join  (... rows=998018 loops=1)        ← joins ~1 million rows
 Execution Time: 310.582 ms

-- 5b
   ->  GroupAggregate  (... rows=6 loops=1)
         ->  Hash Join  (... rows=1950 loops=1)          ← joins 1,950 rows
               ->  Hash
                     ->  HashAggregate  (... rows=1951 loops=1)
 Execution Time: 194.802 ms
```

| | 5a: join → group | 5b: group → join |
|---|---|---|
| Rows entering the join | 998,018 | 1,950 |
| Time | ~310 ms | ~195 ms |

- Both return the same 6 rows (prove it: Step 5c → `0 | 0`):

```text
  category   | payments |    total
-------------+----------+--------------
 UTILITIES   |   187341 | 847990670.46
 FUEL        |   184011 | 832215085.61
 TRAVEL      |   182989 | 827319275.31
 ...
```

📌 **Remember:** shrink rows **before** an expensive join. Then prove the totals match.

---

## Step 6 — CTEs (`WITH`): inlined or materialized?

❓ A CTE `merchant_sales` totals **every** merchant. We ask for **one**. Does PostgreSQL total all 1,951?

▶️ **Run**

```sql
-- 6a. Default (CTE used once)
EXPLAIN (ANALYZE, BUFFERS)
WITH merchant_sales AS (
    SELECT payee_account, count(*) AS payments, sum(amount) AS total
    FROM transactions
    GROUP BY payee_account
)
SELECT * FROM merchant_sales
WHERE payee_account = 'merchant7';

-- 6b. Same, but WITH merchant_sales AS MATERIALIZED (...)
```

👀 **See** (trimmed)

```text
-- 6a default: the filter moved INSIDE the CTE
 GroupAggregate  (... rows=1 loops=1)
   ->  Bitmap Heap Scan on transactions  (... rows=4397 loops=1)
         ->  Bitmap Index Scan on idx_txn_payee
               Index Cond: (payee_account = 'merchant7'::text)
 Execution Time: 2.653 ms

-- 6b MATERIALIZED: compute everything, then filter
 CTE Scan on merchant_sales  (... rows=1 loops=1)
   Filter: (payee_account = 'merchant7'::text)
   Rows Removed by Filter: 1950
   CTE merchant_sales
     ->  HashAggregate  (... rows=1951 loops=1)
           ->  Seq Scan on transactions  (... rows=1000000 loops=1)
 Execution Time: 193.134 ms
```

| Mode | What happens | Time |
|---|---|---|
| Default, CTE used **once** | Merged into the query; filter pushed down | 2.7 ms |
| `MATERIALIZED` | Whole CTE built first, then filtered | 193 ms |
| Default, CTE used **twice** | Built once, reused (`CTE Scan` twice) | Step 6c |
| `NOT MATERIALIZED` | Forced merge, even when used twice | Step 6c |

- `CTE Scan` in a plan = the CTE was **materialized**.
- Use `MATERIALIZED` only when the CTE is expensive **and** used many times.

📌 **Remember:** a CTE is for readability. Let PostgreSQL merge it, unless you have measured otherwise.

---

## Step 7 — Top-N per group

❓ What is the **latest payment of every payer**?

▶️ **Run**

```sql
-- 7a. row_number(): works in every database
SELECT payer_account, txn_id, txn_ts, amount
FROM (SELECT payer_account, txn_id, txn_ts, amount,
             row_number() OVER (PARTITION BY payer_account
                                ORDER BY txn_ts DESC, txn_id DESC) AS rn
      FROM transactions) ranked
WHERE rn = 1;

-- 7b. DISTINCT ON: PostgreSQL only, shorter
SELECT DISTINCT ON (payer_account)
       payer_account, txn_id, txn_ts, amount
FROM transactions
ORDER BY payer_account, txn_ts DESC, txn_id DESC;
```

👀 **See** (with `EXPLAIN (ANALYZE, BUFFERS)`, trimmed)

```text
-- 7a
 Subquery Scan on ranked  (... rows=9900 loops=1)
   ->  WindowAgg  (... rows=9900 loops=1)
         ->  Sort  (... rows=1000000 loops=1)
               Sort Method: external merge  Disk: 48256kB
 Execution Time: 1175.107 ms

-- 7b
 Unique  (... rows=9900 loops=1)
   ->  Sort  (... rows=1000000 loops=1)
         Sort Method: external merge  Disk: 48256kB
 Execution Time: 1151.951 ms
```

- Same work: sort **1,000,000 rows** (spills 48 MB to disk), keep 1 per payer → **9,900 rows**.
- Same rows: Step 7c → `0 | 0`.
- `txn_id DESC` is the **tie-breaker**: without it, two payments at the same second could pick a random winner.

❓ Latest **3** payments of **every merchant**: can we avoid sorting 1M rows?

▶️ **Run**

```sql
CREATE INDEX idx_txn_payee_ts ON transactions (payee_account, txn_ts DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, last3.txn_id, last3.txn_ts, last3.amount
FROM merchants m
CROSS JOIN LATERAL (
    SELECT t.txn_id, t.txn_ts, t.amount
    FROM transactions t
    WHERE t.payee_account = m.merchant_account
    ORDER BY t.txn_ts DESC
    LIMIT 3
) last3;
```

👀 **See** (trimmed)

```text
 Nested Loop  (... actual time=0.025..16.551 rows=5850 loops=1)
   ->  Seq Scan on merchants m  (... rows=2000 loops=1)
   ->  Limit  (... rows=3 loops=2000)
         ->  Index Scan using idx_txn_payee_ts on transactions t  (... rows=3 loops=2000)
               Index Cond: (payee_account = m.merchant_account)
 Execution Time: 16.743 ms
```

- `LATERAL` = "for each merchant, run this small query".
- Each run reads **3 index entries** and stops → 5,850 rows (1,950 × 3) in **17 ms**.

| Pattern | Best when |
|---|---|
| `row_number()` | Any database; top 1, 2, 3… |
| `DISTINCT ON` | PostgreSQL; top **1** only; shortest SQL |
| `LATERAL ... LIMIT n` + index | Few rows per group, **index on (group, order)** |

📌 **Remember:** top-N per group = "rank and filter" or "for each group, take N from an index".

---

## Step 8 — Pagination: `OFFSET` vs keyset

❓ The busy payer `u42@bank` has **10,216** payments. Page 451 (rows 9,001–9,020): how much work?

▶️ **Run**

```sql
CREATE INDEX idx_txn_payer_ts_id
    ON transactions (payer_account, txn_ts DESC, txn_id DESC);

-- 8a. OFFSET
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC, txn_id DESC
OFFSET 9000 LIMIT 20;
```

👀 **See** (trimmed)

```text
 Limit  (... actual time=7.332..7.335 rows=20 loops=1)
   Buffers: shared hit=7017 read=65
   ->  Sort  (... rows=9020 loops=1)
         ->  Bitmap Heap Scan on transactions  (... rows=10216 loops=1)
 Execution Time: 7.345 ms
```

- To **skip** 9,000 rows, PostgreSQL must still **read** them: 7,082 pages for 20 rows.

▶️ **Run**: keyset ("continue after the last row I saw")

```sql
-- remember the last row of the previous page (row 9,000)
SELECT txn_ts AS last_ts, txn_id AS last_id
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC, txn_id DESC
OFFSET 8999 LIMIT 1 \gset

-- 8b. continue right after it
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM transactions
WHERE payer_account = 'u42@bank'
  AND (txn_ts, txn_id) < (:'last_ts', :last_id)
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 20;
```

- `\gset` stores the result in psql variables `:last_ts` = `'2026-01-11 05:57:53'`, `:last_id` = `114483`. In an app, the screen remembers them.

👀 **See**

```text
 Limit  (... actual time=0.006..0.012 rows=20 loops=1)
   Buffers: shared hit=15
   ->  Index Scan using idx_txn_payer_ts_id on transactions  (... rows=20 loops=1)
         Index Cond: ((payer_account = 'u42@bank'::text) AND
                      (ROW(txn_ts, txn_id) < ROW('2026-01-11 05:57:53'::timestamp, 114483)))
 Execution Time: 0.024 ms
```

| | `OFFSET 9000` | Keyset |
|---|---|---|
| Pages | 7,082 | **15** |
| Time | ~7.3 ms | **~0.02 ms** |
| Gets slower on later pages? | Yes | No |
| Jump to "page 451" directly? | Yes | No (next/previous only) |

- Same 20 rows: Step 8c → `0 | 0`.

📌 **Remember:** `OFFSET n` reads and throws away n rows. Keyset **seeks** straight to the next row.

---

## Step 9 — Statistics: when the planner's guess is wrong

❓ Why did Lab 01's estimate for **FAILED + WEB** miss by 3×?

▶️ **Run**

```sql
SELECT attname, most_common_vals, most_common_freqs
FROM pg_stats
WHERE tablename = 'transactions' AND attname IN ('status', 'channel');

EXPLAIN ANALYZE
SELECT count(*) FROM transactions
WHERE status = 'FAILED' AND channel = 'WEB';
```

👀 **See**

```text
 attname |     most_common_vals     |         most_common_freqs
---------+--------------------------+-----------------------------------
 status  | {SUCCESS,FAILED,PENDING} | {0.9404333,0.0488,0.010766666}
 channel | {APP,UPI_QR,WEB}         | {0.6045333,0.24543333,0.15003334}

   ->  Seq Scan on transactions  (... rows=7322 ...) (actual ... rows=22708 loops=1)
```

- The planner multiplies: 4.9% FAILED × 15% WEB × 1,000,000 ≈ **7,300**.
- Reality: **WEB fails 3× more often** → **22,708**. The columns are **related**.

▶️ **Run**

```sql
CREATE STATISTICS st_status_channel (mcv) ON status, channel FROM transactions;
ANALYZE transactions;

EXPLAIN ANALYZE
SELECT count(*) FROM transactions
WHERE status = 'FAILED' AND channel = 'WEB';
```

👀 **See**

```text
   ->  Seq Scan on transactions  (... rows=23467 ...) (actual ... rows=22708 loops=1)
```

- Estimate is now **~23,500 vs 22,708**: close.
- Your estimate may differ slightly: `ANALYZE` reads a **random sample** of rows.
- Why care? Estimates drive plan choices: join type (Lab 03), index vs scan (Lab 02). Wrong guess → wrong plan.

📌 **Remember:** if `rows=` (guess) is far from actual rows, fix the **statistics** first, then the SQL.

---

## Lab 04 summary

| Problem in the plan | Rewrite | Proof |
|---|---|---|
| `SubPlan` with `loops=2000` of full scans | Group once + `LEFT JOIN`, or index the subquery | `EXCEPT ALL` → `0 \| 0` |
| Join on 1M rows, then group | Group first, then join | `EXCEPT ALL` → `0 \| 0` |
| `CTE Scan` + `Rows Removed by Filter` | Let the CTE inline (remove `MATERIALIZED`) | Same rows |
| Big `Sort` for "latest per group" | `DISTINCT ON`, or `LATERAL` + index | `EXCEPT ALL` → `0 \| 0` |
| `OFFSET` reading thousands of rows | Keyset: `(ts, id) < (:last_ts, :last_id)` | `EXCEPT ALL` → `0 \| 0` |
| Estimate far from actual | `CREATE STATISTICS` + `ANALYZE` | Compare `rows=` |

### The rewrite routine

1. **Measure** the original: `EXPLAIN (ANALYZE, BUFFERS)`
2. **Find** the waste: repeated `SubPlan`, huge join input, `CTE Scan`, big `Sort`, big `OFFSET`
3. **Rewrite** one thing
4. **Prove** same rows: `EXCEPT ALL` both ways → `0 | 0`
5. **Measure** again: pages and time

---

## Try it yourself

- **T1.** Rewrite as "group once, then join", and prove it with the template:
  ```sql
  SELECT a.account_id,
         (SELECT max(t.amount) FROM transactions t
          WHERE t.payer_account = a.account_id) AS biggest_payment
  FROM accounts a;
  ```
  - 100 accounts never paid. What must `biggest_payment` be for them: `0` or `NULL`?
- **T2.** Change Step 7a to return the latest **2** payments per payer. How many rows? Why can't `DISTINCT ON` do this?
- **T3.** Run Step 6b's `MATERIALIZED` CTE for `'merchant1'` and for `'merchant1500'`. Is the time different? Why not?
- **T4.** Keyset: fetch the **next** page after Step 8b. (Hint: `\gset` the last row of that page.)

---

## Common mistakes

- ❌ Rewriting without proving → always run `EXCEPT ALL` both ways
- ❌ `JOIN` instead of `LEFT JOIN` → rows with no match disappear
- ❌ `COALESCE(x, 0)` everywhere → `count` should be 0, but `max` of nothing is `NULL`
- ❌ Using `EXCEPT` instead of `EXCEPT ALL` → misses duplicate differences
- ❌ No tie-breaker in `ORDER BY` → "latest" row and pages change between runs
- ❌ Adding `MATERIALIZED` "for speed" → blocks filter pushdown
- ❌ Keyset on `txn_ts` alone → rows with the same timestamp get skipped
- ❌ `EXPLAIN ANALYZE` on the 2,000-loop correlated query → runs for over a minute

---

## Quick quiz

1. A plan shows `SubPlan 1` and `loops=2000`. What does that mean?
2. The rewrite returns `only_in_original = 50`, `only_in_rewrite = 0`. Is the rewrite correct?
3. Why does the default CTE in Step 6a take 2.7 ms but the `MATERIALIZED` one 193 ms?
4. Which is cheaper for page 451: `OFFSET 9000 LIMIT 20` or keyset? Why?
5. Estimate `rows=7322`, actual `rows=22708`. What is the fix?

**Next:** Lab 05 — Capstone: The Slow Dashboard
