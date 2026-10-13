# Lab 03 — Joins

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab03.sql`

## The story

- Support now wants **`u1000@bank`'s payments with merchant names**.
- Managers want reports that combine **accounts + payments + merchants**.
- **Your job:** see *how* PostgreSQL joins tables, and avoid the classic join mistakes.

## You will be able to

- Recognise the 3 join methods: **Nested Loop**, **Hash Join**, **Merge Join**
- Say when each one wins
- Index **foreign key** columns (PostgreSQL does not do it for you)
- Avoid the **LEFT JOIN** trap and the **NOT IN + NULL** trap
- Use **EXISTS / NOT EXISTS** (semi join / anti join)
- Spot a join that runs out of memory (`Batches`, `temp`)

## How every step works

1. ❓ **Question** → 2. 🤔 **Predict** → 3. ▶️ **Run** → 4. 👀 **See** → 5. 📌 **Remember**

> Your milliseconds will differ from the trainer's. **Rows, pages and plan shapes will match.**

---

## Step 0 — Clean start

▶️ **Run**

```sql
\i sql/reset.sql
SET max_parallel_workers_per_gather = 0;
```

- No extra indexes; only the 3 primary keys.
- Parallel query off for the whole lab (simpler plans).

---

## Step 1 — Nested Loop: one customer's payments + merchant names

❓ Show `u1000@bank`'s payments with the merchant name.

🤔 **Predict:** for each payment, how will PostgreSQL find the merchant?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT t.txn_id, t.amount, m.merchant_name
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u1000@bank';
```

👀 **See**

```text
 Nested Loop  (... actual time=0.307..41.178 rows=102 loops=1)
   Buffers: shared hit=12912
   ->  Seq Scan on transactions t  (... rows=103 loops=1)                     ① outer
         Filter: (payer_account = 'u1000@bank'::text)
         Rows Removed by Filter: 999897
         Buffers: shared hit=12606
   ->  Index Scan using merchants_pkey on merchants m  (... rows=1 loops=103) ② inner
         Index Cond: (merchant_account = t.payee_account)
         Buffers: shared hit=306
 Execution Time: 41.189 ms
```

- **Nested Loop** = for **each** outer row, look up matching inner rows.
  - ① outer: find u1000's 103 payments (slow part: full scan, no index yet)
  - ② inner: look up the merchant **103 times** (`loops=103`) via the primary key → 3 pages each
- 📞 **Analogy:** one phone call per payment: "Who is merchant 17?"
- Why **102** rows, not 103? One payment is PENDING with **no payee** (`NULL`). An inner join drops it.

```sql
SELECT count(*) AS payments, count(t.payee_account) AS with_payee
FROM transactions t WHERE t.payer_account = 'u1000@bank';      -- 103 | 102
```

📌 **Remember:** Nested Loop is great when the **outer side is small** and the **inner side has an index**.

---

## Step 2 — Hash Join: totals per merchant category

❓ Total spend per category, over **all 1,000,000** payments.

🤔 **Predict:** 1 million phone calls (Nested Loop)? Or something smarter?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;
```

👀 **See** (trimmed)

```text
 Sort  (... rows=6 loops=1)
   ->  HashAggregate  (... rows=6 loops=1)
         ->  Hash Join  (... actual time=0.280..188.868 rows=998018 loops=1)
               Hash Cond: (t.payee_account = m.merchant_account)
               ->  Seq Scan on transactions t  (... rows=1000000 loops=1)      ② probe
               ->  Hash  (... rows=2000 loops=1)                                ① build
                     Buckets: 2048  Batches: 1  Memory Usage: 119kB
                     ->  Seq Scan on merchants m  (... rows=2000 loops=1)
 Execution Time: 304.853 ms
```

- **Hash Join** works in 2 phases:
  - ① **Build:** read the small table (2,000 merchants) into a memory lookup table (`Hash`)
  - ② **Probe:** read each payment once, look up its merchant in memory
- 🐍 **Analogy:** a Python dictionary: `merchants = {"merchant1": "FUEL", ...}` then `merchants[payee]`.
- `Batches: 1` + `Memory Usage: 119kB` → the lookup table fits in memory. Good.
- Result: 998,018 rows (1,982 NULL payees dropped) → 6 categories.

📌 **Remember:** Hash Join is the workhorse for **big + big** or **big + small** joins with `=`.

---

## Step 3 — Merge Join: force it, just to see it

❓ What does the third join method look like, and why didn't PostgreSQL choose it?

▶️ **Run**

```sql
BEGIN;
SET LOCAL enable_hashjoin = off;
SET LOCAL enable_nestloop = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;

ROLLBACK;
```

👀 **See** (trimmed)

```text
         ->  Merge Join  (... actual time=1096.268..1256.752 rows=998018 loops=1)
               Merge Cond: (t.payee_account = m.merchant_account)
               ->  Sort  (... rows=998019 loops=1)
                     Sort Key: t.payee_account
                     Sort Method: external merge  Disk: 28664kB
                     ->  Seq Scan on transactions t  (... rows=1000000 loops=1)
               ->  Sort  (... rows=2000 loops=1)
                     Sort Method: quicksort  Memory: 128kB
                     ->  Seq Scan on merchants m  (... rows=2000 loops=1)
 Execution Time: 1382.149 ms
```

- **Merge Join** = sort both sides by the join key, then walk down both lists together.
- 🧾 **Analogy:** two sorted queues: compare the fronts, step forward, repeat.
- Here it needed to **sort 1 million rows**, and that sort spilled to **disk** (28 MB) → **1,382 ms vs 305 ms**.
- That is why the planner picked Hash Join. Ignore the `JIT:` lines at the bottom.
- `SET LOCAL` + `ROLLBACK` → the settings apply to this transaction only.

📌 **Remember:** Merge Join wins when both sides are **already sorted** (e.g. by an index). Turning join methods off is for **learning only**.

---

## Step 4 — Foreign keys are NOT indexed automatically

❓ Top 5 CORPORATE customers in Hyderabad, by amount paid.

🤔 **Predict:** `payer_account` is a foreign key. Is it indexed?

▶️ **Run**

```sql
\d transactions
```

- `Indexes:` shows only `transactions_pkey`.
- `Foreign-key constraints:` shows `transactions_payer_fk` and `transactions_payee_fk`, **with no index**.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT a.account_id, a.holder_name, count(*) AS payments, sum(t.amount) AS total
FROM accounts a
JOIN transactions t ON t.payer_account = a.account_id
WHERE a.segment = 'CORPORATE' AND a.city = 'Hyderabad'
GROUP BY a.account_id, a.holder_name
ORDER BY total DESC
LIMIT 5;
```

👀 **See (before):** `Hash Join` + `Seq Scan on transactions` (1,000,000 rows), **12,699 pages**, ~110 ms

- Only **48 accounts** match, but all 1,000,000 payments are read.

▶️ **Run:** index the foreign key, then the same query again

```sql
CREATE INDEX idx_txn_payer ON transactions (payer_account);
```

👀 **See (after)**

```text
               ->  Nested Loop  (... actual time=0.042..4.119 rows=4541 loops=1)
                     ->  Seq Scan on accounts a  (... rows=48 loops=1)
                           Filter: ((segment = 'CORPORATE'::text) AND (city = 'Hyderabad'::text))
                     ->  Bitmap Heap Scan on transactions t  (... rows=95 loops=48)
                           ->  Bitmap Index Scan on idx_txn_payer  (... rows=95 loops=48)
                                 Index Cond: (payer_account = a.account_id)
 Execution Time: 4.745 ms
```

| | Before | After `idx_txn_payer` |
|---|---|---|
| Join | Hash Join | Nested Loop (index lookup ×48) |
| Pages | 12,699 | 4,760 |
| Time | ~110 ms | ~5 ms |
| Result | 5 rows | same 5 rows |

📌 **Remember:** PostgreSQL indexes **primary keys** automatically, **never foreign keys**. Index FK columns you join on.

---

## Step 5 — Three tables: join order and filter pushdown

❓ PREMIUM customers paying **Mumbai** merchants: totals per category.

🤔 **Predict:** does the order you write the tables in matter?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN accounts  a ON a.account_id       = t.payer_account
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE a.segment = 'PREMIUM'
  AND m.city    = 'Mumbai'
GROUP BY m.category
ORDER BY total DESC;
```

👀 **See** (trimmed)

```text
         ->  Hash Join  (... rows=18397 loops=1)                              ③
               Hash Cond: (t.payer_account = a.account_id)
               ->  Hash Join  (... rows=127121 loops=1)                       ②
                     Hash Cond: (t.payee_account = m.merchant_account)
                     ->  Seq Scan on transactions t  (... rows=1000000 loops=1)
                     ->  Hash
                           ->  Seq Scan on merchants m  (... rows=281 loops=1)   ①
                                 Filter: (city = 'Mumbai'::text)
               ->  Hash
                     ->  Seq Scan on accounts a  (... rows=1500 loops=1)         ①
                           Filter: (segment = 'PREMIUM'::text)
```

- **Filter pushdown:** the `WHERE` conditions are applied **inside the scans** (①), before any join.
  - 2,000 merchants → 281 (Mumbai); 10,000 accounts → 1,500 (PREMIUM)
- **Join order:** PostgreSQL chose payments ⨝ Mumbai merchants first (②: 127,121 rows), then ⨝ PREMIUM accounts (③: 18,397 rows).
- Run the second query in `sql/lab03.sql` (tables written in a different order) → **identical plan**.

📌 **Remember:** for inner joins, the planner picks the join order. Your job: **good filters** and **useful indexes**.

---

## Step 6 — The LEFT JOIN trap: ON vs WHERE

❓ FAILED payments per merchant on 31 March, listing **all 2,000 merchants** (0 if none).

🤔 **Predict:** does it matter if the conditions go in `ON` or in `WHERE`?

▶️ **Run** (both are in `sql/lab03.sql`)

```sql
-- A: conditions in ON
SELECT m.merchant_account, count(t.txn_id) AS failed
FROM merchants m
LEFT JOIN transactions t
       ON t.payee_account = m.merchant_account
      AND t.status = 'FAILED'
      AND t.txn_ts >= '2026-03-31'
GROUP BY m.merchant_account;

-- B: conditions in WHERE
SELECT m.merchant_account, count(t.txn_id) AS failed
FROM merchants m
LEFT JOIN transactions t
       ON t.payee_account = m.merchant_account
WHERE t.status = 'FAILED'
  AND t.txn_ts >= '2026-03-31'
GROUP BY m.merchant_account;
```

👀 **See**

| Version | Merchants listed |
|---|---|
| A: conditions in `ON` | **2,000** ✅ |
| B: conditions in `WHERE` | **439** ❌ |

- In B, merchants with no failed payment get `NULL` for `t.status`.
- `WHERE t.status = 'FAILED'` throws those rows away → the LEFT JOIN silently becomes an inner join.
- **1,561 merchants** disappeared from the report.

📌 **Remember:** with LEFT JOIN, conditions on the **right-hand table** go in **`ON`**, not `WHERE`.

---

## Step 7 — EXISTS vs JOIN + DISTINCT (semi join)

❓ Which **Pune** merchants have received **at least one** payment?

▶️ **Run:** first index the other foreign key

```sql
CREATE INDEX idx_txn_payee ON transactions (payee_account);
```

🤔 **Predict:** which is faster: join everything then remove duplicates, or ask "is there at least one"?

```sql
-- A: join every payment, then remove duplicates
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT m.merchant_account, m.merchant_name
FROM merchants m
JOIN transactions t ON t.payee_account = m.merchant_account
WHERE m.city = 'Pune';

-- B: ask only "is there at least one?"
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.merchant_name
FROM merchants m
WHERE m.city = 'Pune'
  AND EXISTS (SELECT 1 FROM transactions t
              WHERE t.payee_account = m.merchant_account);
```

👀 **See**

```text
A:  HashAggregate  (... rows=193 loops=1)
      ->  Nested Loop  (... rows=97662 loops=1)
            ->  Index Only Scan using idx_txn_payee ... (... rows=483 loops=202)
    Execution Time: 22.200 ms

B:  Nested Loop Semi Join  (... rows=193 loops=1)
      ->  Index Only Scan using idx_txn_payee ... (... rows=1 loops=202)
    Execution Time: 0.659 ms
```

| | JOIN + DISTINCT | EXISTS |
|---|---|---|
| Rows produced before de-duplication | 97,662 | — |
| Rows read per merchant | ~483 | **1** (stops at first match) |
| Result | 193 merchants | same 193 merchants |
| Time | ~22 ms | ~0.7 ms |

- **Semi Join** = "return the left row once if **any** match exists".

📌 **Remember:** need "has at least one?" → use **EXISTS**, not `JOIN` + `DISTINCT`.

---

## Step 8 — NOT EXISTS vs NOT IN (the NULL trap)

❓ Which merchants have **never** been paid?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.merchant_name
FROM merchants m
WHERE NOT EXISTS (SELECT 1 FROM transactions t
                  WHERE t.payee_account = m.merchant_account);
```

👀 **See**

```text
 Nested Loop Anti Join  (... actual time=6.073..6.176 rows=50 loops=1)
   ->  Seq Scan on merchants m  (... rows=2000 loops=1)
   ->  Index Only Scan using idx_txn_payee on transactions t  (... rows=1 loops=2000)
 Execution Time: 6.183 ms
```

- **50 merchants** (merchant1951 … merchant2000). **Anti Join** = "keep the row if **no** match exists".

🤔 **Predict:** `NOT IN` should give the same 50… right?

```sql
SELECT 'merchant1' NOT IN ('merchant2', NULL) AS is_it_true;     -- NULL (not true!)
```

- `x NOT IN (..., NULL)` is **never true**: SQL can't be sure `x` isn't the unknown value.
- `payee_account` has **1,982 NULLs**, so `NOT IN (SELECT payee_account ...)` returns **0 rows**.

▶️ **Run:** proof on real data (fast version: merchants with no PENDING payment)

| Query | Result |
|---|---|
| `NOT EXISTS (... status = 'PENDING')` | **155** ✅ |
| `NOT IN (SELECT payee_account ... status = 'PENDING')` | **0** ❌ |

▶️ **Run:** the full `NOT IN` with **`EXPLAIN` only** (never with `ANALYZE`)

```text
 Seq Scan on merchants m  (cost=0.42..30955045.43 rows=1000 width=30)
   Filter: (NOT (ANY (merchant_account = (SubPlan 1).col1)))
   SubPlan 1
     ->  Materialize  (cost=0.42..28455.42 rows=1000000 width=11)
```

- Cost **30,955,045** vs **1,012** for NOT EXISTS: it re-reads 1M rows for each merchant.
- On the trainer laptop it ran **86 seconds**, and returned **0 rows**. Wrong *and* slow.

📌 **Remember:** use **NOT EXISTS**. `NOT IN` + a column that can be NULL = wrong answer.

---

## Step 9 — Memory: when the hash does not fit

❓ Payments per customer segment. What if the join gets less memory?

▶️ **Run**

```sql
SHOW work_mem;                     -- 4MB (memory per sort/hash step)

EXPLAIN (ANALYZE, BUFFERS)
SELECT a.segment, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN accounts a ON a.account_id = t.payer_account
GROUP BY a.segment;

BEGIN;
SET LOCAL work_mem = '64kB';
-- same EXPLAIN again
ROLLBACK;
```

👀 **See**

| | `work_mem = 4MB` | `work_mem = 64kB` |
|---|---|---|
| Hash node | `Batches: 1  Memory Usage: 626kB` | `Batches: 8  Memory Usage: 81kB` |
| Temp files | none | `temp read=3990 written=3990` |
| Time | ~297 ms | ~364 ms |

- `Batches: 8` → the 10,000-account lookup table didn't fit → split into 8 parts, using **temp files on disk**.
- Same family as Step 3's `Sort Method: external merge  Disk: 28664kB`.

📌 **Remember:** `Batches > 1`, `external merge`, `temp read/written` = **spilled to disk**. Fix the query or give that query more `work_mem`. Don't raise `work_mem` server-wide blindly (it is per step, per user).

---

## Lab 03 summary

| Join method | How it works | Wins when | Watch for |
|---|---|---|---|
| **Nested Loop** | For each outer row, look up inner rows | Few outer rows + index on inner | `loops=` very large, no inner index |
| **Hash Join** | Build lookup table from one side, probe with the other | Big joins on `=` | `Batches > 1` (memory spill) |
| **Merge Join** | Walk two sorted lists together | Both sides already sorted | Big `Sort` / `external merge` |

| Pattern | Use |
|---|---|
| Join on a foreign key | **Index the FK column** |
| "Has at least one?" | `EXISTS` → **Semi Join** |
| "Has none?" | `NOT EXISTS` → **Anti Join**, never `NOT IN` on nullable columns |
| LEFT JOIN + filter on right table | Put the filter in **`ON`** |

---

## Try it yourself

- **T1.** Re-run the Step 1 query now (`idx_txn_payer` exists). Which join appears? Why did it change?
- **T2.** Which **accounts** have never made a payment? Write it with `NOT EXISTS`. How many rows? Which join node?
- **T3.** Using the correct Step 6 report (version A), how many merchants had **zero** failed payments on 31 March?
- **T4.** Add `WHERE t.payee_account IS NOT NULL` inside the Step 8D `NOT IN` subquery. Run `EXPLAIN` (not `ANALYZE`).
  - Is the answer correct now? Is the plan cheap? What is the better fix?

---

## Common mistakes

- ❌ Assuming foreign keys are indexed → only primary keys / unique constraints are
- ❌ Filtering the right-hand table of a LEFT JOIN in `WHERE` → rows silently disappear
- ❌ `NOT IN (subquery)` on a nullable column → 0 rows
- ❌ `JOIN` + `DISTINCT` just to test existence → use `EXISTS`
- ❌ Leaving `enable_hashjoin = off` in a session → only ever inside `BEGIN ... ROLLBACK`
- ❌ Expecting the written table order to control the join order (inner joins)
- ❌ Raising `work_mem` for the whole server to fix one query

---

## Quick quiz

1. A Nested Loop shows `loops=103` on the inner Index Scan. What does that mean?
2. In a Hash Join, which table usually goes into the `Hash` node: the big one or the small one?
3. `Batches: 8` on a Hash node: good or bad? Why?
4. Does PostgreSQL automatically index foreign key columns?
5. `SELECT 5 NOT IN (1, 2, NULL)` returns what?
6. You need "customers who bought at least once". `JOIN` + `DISTINCT` or `EXISTS`?

**Next:** Lab 04 — Rewriting Queries for Performance
