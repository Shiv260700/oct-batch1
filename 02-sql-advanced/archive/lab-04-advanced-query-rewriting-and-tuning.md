# Lab 04 — Advanced Query Rewriting and Performance Tuning (PostgreSQL)

**Course:** Advanced SQL — PostgreSQL  
**Lab:** 04  
**Level:** Intermediate to advanced  
**Database:** `paylab`  
**Focus:** Make SQL more efficient without changing the business result. Compare scans, subqueries, CTEs, window functions, top-N queries, keyset pagination, and statistics using real execution plans.

## Learning objectives

By the end of this lab, participants will be able to:

- Establish a repeatable performance baseline with `EXPLAIN (ANALYZE, BUFFERS)`.
- Recognize predicates that prevent efficient index usage.
- Use selective composite and partial indexes for reporting queries.
- Compare `IN`, `EXISTS`, correlated subqueries, and semijoins without changing result semantics.
- Distinguish `MATERIALIZED` and `NOT MATERIALIZED` CTE behavior.
- Tune pagination, top-N-per-group, and window-function workloads.
- Find poor row estimates and test improved statistics.
- Validate **both** correctness and performance after a rewrite.

## Prerequisites and safety

- PostgreSQL running, connected to database `paylab`.
- Lab 03 completed; `lab03_transactions`, `lab03_merchants`, and `lab03_accounts` must exist.
- Ability to create local practice tables and indexes.
- Run SQL blocks **in order**. Execute one statement at a time in pgAdmin where indicated.
- Commands beginning `EXPLAIN (ANALYZE...)` **actually execute** the query. All measured queries in this lab are read-only.
- Your timings and chosen plans may vary with PostgreSQL version, cache warmth, table contents, and machine resources.

> **Schema compatibility:** This guide uses the columns `txn_id`, `payer_account`, `payee_account`, `amount`, `txn_ts`, `status`, and `channel` inherited from Lab 01. Verify them first. If Lab 01 uses a different transaction ID name, replace `txn_id` consistently in the exercises.

---

## Exercise 1 — Prepare an isolated, measurable workload

**Business story:** A payment platform generates transaction lookups, active-channel dashboards, top-spender lists, merchant reports, and paginated history. We want these requests to become faster without changing the answer.

### 1.1 Inspect the source schema

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'lab03_transactions'
ORDER BY ordinal_position;

SELECT count(*) AS source_rows FROM lab03_transactions;
SELECT min(txn_ts), max(txn_ts) FROM lab03_transactions;
```

### 1.2 Copy Lab 03 transactions

```sql
DROP TABLE IF EXISTS lab04_transactions;

CREATE TABLE lab04_transactions AS
SELECT * FROM lab03_transactions;

ANALYZE lab04_transactions;

SELECT count(*) AS lab04_rows FROM lab04_transactions;
```

**Expected:** Around 300,000 transaction rows with the full Lab 03 dataset. The copied table starts without the Lab 03 indexes, so experiments remain independent.

### 1.3 Inspect real data distributions

```sql
SELECT channel, count(*) AS rows
FROM lab04_transactions
GROUP BY channel ORDER BY rows DESC;

SELECT status, count(*) AS rows
FROM lab04_transactions
GROUP BY status ORDER BY rows DESC;

SELECT payer_account, count(*) AS rows
FROM lab04_transactions
GROUP BY payer_account ORDER BY rows DESC LIMIT 5;
```

**Observe:** Which values are common and rare? A condition matching 0.01% of a table is very different from one matching 40%.

**Checkpoint:** Write down the row count, one `payer_account` with transactions, and two channel/status values you observed.

---

## Exercise 2 — Build a reliable baseline

### 2.1 Choose a real payer value

```sql
SELECT payer_account, count(*) AS txn_count
FROM lab04_transactions
GROUP BY payer_account
ORDER BY txn_count DESC, payer_account
LIMIT 5;
```

For examples below, substitute one of these values for `'YOUR_PAYER'`.

### 2.2 Baseline scan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount, txn_ts
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER';
```

Record:

| Metric | Before tuning |
|---|---|
| Access method (`Seq Scan`, `Parallel Seq Scan`, etc.) | |
| Estimated rows | |
| Actual rows | |
| Shared hit / read buffers | |
| Planning time | |
| Execution time | |

### 2.3 Index and re-measure

```sql
CREATE INDEX idx_lab04_payer
ON lab04_transactions (payer_account);

ANALYZE lab04_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount, txn_ts
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER';
```

**Expected observation:** A selective payer lookup often switches to `Index Scan`, `Bitmap Index Scan` + `Bitmap Heap Scan`, or another index-based plan. It is **not guaranteed**.

**Trainer explanation:** `cost` is a planner estimate, not milliseconds. `Buffers: shared hit` counts cached page accesses; `read` counts shared-buffer misses that required a page read, which might be fulfilled from the operating-system cache.

---

## Exercise 3 — Avoid non-index-friendly predicates

**Question:** Why can a function on a filtered column cause a table scan?

### 3.1 Create an index on transaction timestamp

```sql
CREATE INDEX idx_lab04_ts ON lab04_transactions(txn_ts);
ANALYZE lab04_transactions;
```

### 3.2 Less index-friendly: cast the column

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM lab04_transactions
WHERE txn_ts::date = DATE '2026-03-15';
```

### 3.3 Range predicate: index-friendly form

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM lab04_transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15 00:00:00'
  AND txn_ts <  TIMESTAMP '2026-03-16 00:00:00';
```

**Why a half-open range?** For a plain `timestamp without time zone`, both forms select the same calendar date. The range form makes the index key directly searchable. If the column is `timestamptz`, choose explicit timezone boundaries first; the semantics of `::date` depend on session timezone.

| Pattern | Typical planner consequence |
|---|---|
| `txn_ts::date = DATE '...'` | Index on raw `txn_ts` may not be useful for the predicate |
| `txn_ts >= ... AND txn_ts < ...` | Ordinary B-tree range scan becomes available |

**Important:** Verify the date is present in your dataset. If it is absent, choose a day returned by `SELECT txn_ts::date, count(*) ... GROUP BY 1 ORDER BY 1 LIMIT 10;`.

---

## Exercise 4 — Composite indexes and `ORDER BY ... LIMIT`

**Business question:** Show the latest 10 transactions of a payer.

### 4.1 Query with payer-only index

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts, amount
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 10;
```

Check for `Sort` or `top-N heapsort` nodes. Sorting 30 rows is often already cheap.

### 4.2 Composite index matching filter and ordering

```sql
CREATE INDEX idx_lab04_payer_ts_id
ON lab04_transactions (payer_account, txn_ts DESC, txn_id DESC);

ANALYZE lab04_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts, amount
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 10;
```

**Plan story:** Use the equality column first; follow with the columns needed for the ordered output. PostgreSQL may retrieve the first 10 qualifying index entries without sorting the whole payer history.

**Discuss:** Why is `(txn_ts, payer_account)` usually less suitable for this particular query than `(payer_account, txn_ts)`?

---

## Exercise 5 — `EXISTS` instead of join-induced duplicates

**Business question:** List merchants having at least one matching transaction. We need each merchant **once**.

### 5.1 A join that can multiply merchant rows

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT m.merchant_account, m.category
FROM lab03_merchants m
JOIN lab04_transactions t
  ON t.payee_account = m.merchant_account;
```

### 5.2 An existence test

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.category
FROM lab03_merchants m
WHERE EXISTS (
    SELECT 1
    FROM lab04_transactions t
    WHERE t.payee_account = m.merchant_account
);
```

**Expected observation:** `EXISTS` expresses a semijoin: return each merchant if at least one matching transaction exists. PostgreSQL may use `Hash Semi Join`, `Nested Loop Semi Join`, or rewrite the query differently.

**Check correctness (set comparison):**

```sql
WITH a AS (
  SELECT DISTINCT m.merchant_account, m.category
  FROM lab03_merchants m
  JOIN lab04_transactions t
    ON t.payee_account = m.merchant_account
),
b AS (
  SELECT m.merchant_account, m.category
  FROM lab03_merchants m
  WHERE EXISTS (
    SELECT 1 FROM lab04_transactions t
    WHERE t.payee_account = m.merchant_account
  )
)
SELECT
  (SELECT count(*) FROM (SELECT * FROM a EXCEPT SELECT * FROM b) x) AS only_a,
  (SELECT count(*) FROM (SELECT * FROM b EXCEPT SELECT * FROM a) x) AS only_b;
```

**Expected:** `0, 0` if both are equivalent. `EXISTS` is **not** a drop-in replacement if the result needs counts, sums, or individual joined transaction rows.

---

## Exercise 6 — Correlated subquery vs. pre-aggregated join

**Business question:** For each merchant, report the number of transactions it received.

### 6.1 Correlated subquery

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.category,
       (SELECT count(*)
        FROM lab04_transactions t
        WHERE t.payee_account = m.merchant_account) AS txn_count
FROM lab03_merchants m
LIMIT 50;
```

Look for a subplan and its `loops` count. Here `LIMIT 50` avoids running thousands of repeated full-table scans on an unindexed copy.

### 6.2 Group once, then join

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH counts AS (
    SELECT payee_account, count(*) AS txn_count
    FROM lab04_transactions
    GROUP BY payee_account
)
SELECT m.merchant_account, m.category,
       COALESCE(c.txn_count, 0) AS txn_count
FROM lab03_merchants m
LEFT JOIN counts c
  ON c.payee_account = m.merchant_account
LIMIT 50;
```

**Important comparison caveat:** The two queries can produce equivalent per-merchant counts, but a `LIMIT` without `ORDER BY` does **not** guarantee the same 50 merchants. Compare results using an `ORDER BY m.merchant_account` on both queries, or compare all rows after adding an efficient index on `lab04_transactions(payee_account)`.

### 6.3 Optional: make the correlated lookup efficient

```sql
CREATE INDEX idx_lab04_payee
ON lab04_transactions (payee_account);

ANALYZE lab04_transactions;
```

Rerun the subquery. An indexed repeated lookup can be efficient, so **grouped joins are not automatically faster**.

---

## Exercise 7 — CTE inlining and materialization

A Common Table Expression (`WITH`) improves readability, but may influence the plan.

### 7.1 Default CTE

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH payer_txns AS (
  SELECT * FROM lab04_transactions
  WHERE payer_account = 'YOUR_PAYER'
)
SELECT count(*) FROM payer_txns;
```

In modern PostgreSQL, a simple, side-effect-free CTE referenced once can usually be inlined into its parent query.

### 7.2 Force materialization

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH payer_txns AS MATERIALIZED (
  SELECT * FROM lab04_transactions
  WHERE payer_account = 'YOUR_PAYER'
)
SELECT count(*) FROM payer_txns;
```

### 7.3 Request inlining

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH payer_txns AS NOT MATERIALIZED (
  SELECT * FROM lab04_transactions
  WHERE payer_account = 'YOUR_PAYER'
)
SELECT count(*) FROM payer_txns;
```

| Mode | Meaning |
|---|---|
| Default | Planner may inline eligible single-use CTEs |
| `MATERIALIZED` | Explicit optimization fence; intermediate result produced separately |
| `NOT MATERIALIZED` | Permit merging with parent query when legal; repeated work may result for multiple references |

**Inspect:** Do you see `CTE Scan`? Are predicates pushed into the base scan? Do not treat either hint as a universal performance fix.

---

## Exercise 8 — Window functions: latest transaction per payer

**Business question:** Find the latest transaction for each payer.

### 8.1 Window-function approach

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT payer_account, txn_id, txn_ts, amount
FROM (
  SELECT t.*,
         row_number() OVER (
             PARTITION BY payer_account
             ORDER BY txn_ts DESC, txn_id DESC
         ) AS rn
  FROM lab04_transactions t
) ranked
WHERE rn = 1;
```

**Plan reading:** Look for `WindowAgg`, `Sort`, `Incremental Sort`, or a useful ordered index scan. With an index matching `(payer_account, txn_ts DESC, txn_id DESC)`, sort work may decrease.

### 8.2 PostgreSQL-specific `DISTINCT ON`

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT ON (payer_account)
       payer_account, txn_id, txn_ts, amount
FROM lab04_transactions
ORDER BY payer_account, txn_ts DESC, txn_id DESC;
```

**Check correctness:** Both select the same row per payer when `(txn_ts, txn_id)` consistently determines a unique winner. If there can be ties on both, add another unique tie-breaker to both queries.

**Trade-off:** `DISTINCT ON` can be concise and efficient in PostgreSQL. `row_number()` is more portable and supports top 2, top 3, etc.

---

## Exercise 9 — Pagination: OFFSET vs. keyset

**Business question:** Show a payer's transactions in a deterministic, newest-first order.

> We use `(txn_ts, txn_id)` as the ordering keys. Confirm that `txn_id` is unique per transaction; otherwise use a genuinely unique final ordering key to make pagination stable.

### 9.1 OFFSET pagination

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 10 OFFSET 20;
```

### 9.2 Keyset pagination

First fetch the cursor (the last row of the previous page):

```sql
SELECT txn_ts, txn_id
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 1 OFFSET 19;
```

Then substitute the returned timestamp and transaction ID below:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
  AND (txn_ts, txn_id) <
      (TIMESTAMP '2026-03-15 12:00:00', 'REPLACE_TXN_ID')
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 10;
```

**Important:** Do **not** execute with the example timestamp and placeholder; substitute an actual cursor returned by the previous statement. This form assumes `txn_ts` is a plain timestamp; cast/convert appropriately if `timestamptz`.

| OFFSET | Keyset |
|---|---|
| Easy to jump to arbitrary page numbers | Efficient continuation from a known cursor |
| Large OFFSET may require visiting many skipped rows | Can seek to the cursor using a suitable index |
| Can be unstable under concurrent inserts | More stable continuation, though updates/deletes still matter |

**Checkpoint:** Your sample dataset may have only a few dozen rows per payer. The difference becomes clearer with very large histories; do not claim a speedup if the data does not demonstrate one.

---

## Exercise 10 — Partial index for a targeted report

**Business question:** Only report failed transactions.

### 10.1 Discover status values

```sql
SELECT status, count(*) FROM lab04_transactions
GROUP BY status ORDER BY count(*) DESC;
```

If `FAILED` is absent, choose an existing status and replace it consistently.

### 10.2 Test query before index

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT payer_account, txn_ts, amount
FROM lab04_transactions
WHERE status = 'FAILED'
  AND payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC
LIMIT 10;
```

### 10.3 Add a targeted partial index

```sql
CREATE INDEX idx_lab04_failed_payer_ts
ON lab04_transactions (payer_account, txn_ts DESC)
WHERE status = 'FAILED';

ANALYZE lab04_transactions;
```

Rerun the query. The partial index is usable only where the planner can establish that the query predicate implies `status = 'FAILED'`. A partial index may be smaller and cheaper than a full-table alternative, but adds write overhead and requires a matching workload.

---

## Exercise 11 — Statistics and wrong estimates

### 11.1 Inspect optimizer statistics

```sql
SELECT attname, null_frac, n_distinct, most_common_vals
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename = 'lab04_transactions'
  AND attname IN ('payer_account', 'status', 'channel');
```

### 11.2 Refresh statistics

```sql
ANALYZE lab04_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM lab04_transactions
WHERE status = 'FAILED' AND channel = 'WEB';
```

### 11.3 Optional extended statistics for correlated filters

```sql
CREATE STATISTICS lab04_status_channel_stats
    (dependencies, mcv)
ON status, channel
FROM lab04_transactions;

ANALYZE lab04_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM lab04_transactions
WHERE status = 'FAILED' AND channel = 'WEB';
```

**Observe:** Are estimated rows closer to actual rows? If the synthetic columns are independent, extended stats may make little difference. Not every estimate is wrong, and statistics are not an index.

---

## Exercise 12 — Controlled benchmarking and result verification

For each proposed improvement, use the **same query semantics**, same parameters, and similar operating conditions.

### 12.1 Record repeat runs

Run each version several times; record the median rather than relying on one timing.

| Variant | Query semantics identical? | Plan type | Median time (ms) | Shared hits | Shared reads | Actual rows |
|---|---|---|---:|---:|---:|---:|
| Baseline | Yes | | | | | |
| Rewrite | Yes | | | | | |
| Rewrite + index | Yes | | | | | |

### 12.2 Compare ordered query outputs when needed

For two unordered result sets, `EXCEPT` and `EXCEPT ALL` can test content. `EXCEPT` ignores duplicates; use `EXCEPT ALL` if row multiplicity matters.

```sql
WITH a AS (
    SELECT payer_account, count(*) AS txn_count
    FROM lab04_transactions GROUP BY payer_account
),
b AS (
    SELECT payer_account, count(*) AS txn_count
    FROM lab04_transactions GROUP BY payer_account
)
SELECT
 (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) d) AS only_a,
 (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) d) AS only_b;
```

Replace `a` and `b` with your actual baseline and rewritten SQL. Both counts should be zero for equivalent results.

**Performance reminder:** Filtering to a subset and dropping output columns can make a query faster, but they change the requested work. That is not proof that an equivalent query was optimized.

---

## Independent practice challenges

- [ ] **Challenge A — Latest 5 per account:** Return the latest five transactions for each payer. Compare `row_number()` with `rn <= 5` against alternative approaches.
- [ ] **Challenge B — Merchant existence:** Return distinct merchants that received at least one transaction. Compare `JOIN + DISTINCT` with `EXISTS` and verify equality of results.
- [ ] **Challenge C — Date report:** Compare `txn_ts::date` filtering with a half-open timestamp range, using a day present in the data.
- [ ] **Challenge D — Search + sort:** Show the latest 10 transactions for a payer. Compare payer-only and composite indexes; inspect for `Sort`.
- [ ] **Challenge E — Query equivalence:** Construct a rewrite that returns the same grouped sums; use `EXCEPT ALL` in both directions to verify it.

## Trainer solutions and discussion prompts

### Challenge A — Top 5 transactions per payer

```sql
SELECT payer_account, txn_id, txn_ts, amount
FROM (
    SELECT t.*,
           row_number() OVER (
             PARTITION BY payer_account
             ORDER BY txn_ts DESC, txn_id DESC
           ) AS rn
    FROM lab04_transactions t
) ranked
WHERE rn <= 5
ORDER BY payer_account, txn_ts DESC, txn_id DESC;
```

**Discuss:** Why can `DISTINCT ON` return only *one* row per group, whereas `row_number() <= 5` returns five?

### Challenge B — Merchant existence

```sql
SELECT m.merchant_account, m.category
FROM lab03_merchants m
WHERE EXISTS (
  SELECT 1
  FROM lab04_transactions t
  WHERE t.payee_account = m.merchant_account
);
```

**Discuss:** `EXISTS` asks whether at least one match exists, not how many matches exist.

### Challenge C — Range predicate

```sql
SELECT count(*)
FROM lab04_transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15 00:00:00'
  AND txn_ts <  TIMESTAMP '2026-03-16 00:00:00';
```

**Discuss:** Why does the exclusive upper bound handle all times on the chosen date?

### Challenge D — Composite index

```sql
CREATE INDEX IF NOT EXISTS idx_lab04_payer_ts_id
ON lab04_transactions(payer_account, txn_ts DESC, txn_id DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM lab04_transactions
WHERE payer_account = 'YOUR_PAYER'
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 10;
```

**Discuss:** Why might the planner still choose another path for a very small table or low-selectivity filter?

### Challenge E — Baseline vs rewrite

```sql
-- Baseline: aggregate after joining
SELECT m.category, sum(t.amount) AS total_amount
FROM lab04_transactions t
JOIN lab03_merchants m
  ON m.merchant_account = t.payee_account
GROUP BY m.category;

-- Rewrite: aggregate by payee first, then join and roll up by category
SELECT m.category, sum(x.payee_total) AS total_amount
FROM (
  SELECT payee_account, sum(amount) AS payee_total
  FROM lab04_transactions
  GROUP BY payee_account
) x
JOIN lab03_merchants m
  ON m.merchant_account = x.payee_account
GROUP BY m.category;
```

**Discuss:** Both are equivalent when each merchant account identifies exactly one merchant. `sum()` over floating-point types can show rounding differences due to aggregation order; use appropriate exact numeric types for financial totals. The rewrite is not automatically faster: compare plans.

---

## Troubleshooting

| Symptom | Possible reason | What to do |
|---|---|---|
| `relation lab03_transactions does not exist` | Lab 03 was not initialized | Run Lab 03 setup in `paylab` |
| `column txn_id does not exist` | Lab 01 schema uses a different primary key name | Inspect `information_schema.columns` and adapt examples |
| All payer-filtered queries return 0 rows | Placeholder was not replaced | Choose a payer using Exercise 2.1 |
| Index not selected | Too many matches, tiny table, stale stats, or other path is cheaper | Compare buffers and selectivity; run `ANALYZE` |
| CTE behavior differs | Planner decisions / PostgreSQL version | Inspect actual plan rather than expecting one node |
| Huge slowdown with a correlated subquery | Repeated unindexed lookup | Keep `LIMIT 50` while diagnosing; consider payee index |
| Sorting still appears | Index order does not fully match `ORDER BY` or planner chose another path | Compare exact index keys and sort keys |
| Partial index ignored | Filter does not imply its predicate | Use a compatible status filter and re-check plan |
| Counts differ after rewrite | Duplicates, NULL handling, join multiplicity, or outer-join semantics | Verify with `EXCEPT ALL` and inspect join relationships |

## Completion checklist

- [ ] Created the independent `lab04_transactions` workload.
- [ ] Measured a payer lookup before and after a B-tree index.
- [ ] Replaced a function-on-column date filter with a half-open range.
- [ ] Tested an index matching filtering and ordering.
- [ ] Compared existence queries against `JOIN + DISTINCT`.
- [ ] Compared correlated subquery and grouped join plans.
- [ ] Observed differences between materialized and inline CTEs.
- [ ] Compared `row_number()` and `DISTINCT ON` for latest-per-group.
- [ ] Practiced keyset pagination using a real cursor.
- [ ] Tested a partial index and inspected statistics.
- [ ] Verified that rewrite results were equivalent.
- [ ] Recorded execution times, buffers, and actual rows.

## Optional cleanup

Only run when you no longer need Lab 04 practice data:

```sql
DROP TABLE IF EXISTS lab04_transactions;
DROP STATISTICS IF EXISTS lab04_status_channel_stats;
```

**Key takeaway:** Query tuning is a measured cycle: **understand the request → inspect the plan → make one safe change → verify the result → compare the work performed**.
