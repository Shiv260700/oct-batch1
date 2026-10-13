# Lab 01 — PostgreSQL Execution Plan Fundamentals

**Course:** Advanced SQL — PostgreSQL
**Module:** Understanding query performance  
**Level:** Intermediate (SQL fundamentals assumed)  
**Database:** `paylab` from Lab 00  
**Goal:** Read PostgreSQL execution plans and diagnose where a query spends time before attempting optimization.

## Learning outcomes

By the end of this lab, participants should be able to:

- Explain how PostgreSQL chooses a physical plan for an SQL query.
- Distinguish `EXPLAIN` from `EXPLAIN ANALYZE`.
- Read a plan **from the leaf nodes upward**.
- Recognize `Seq Scan`, `Index Scan`, `Bitmap Heap Scan`, `Sort`, and `Aggregate`.
- Interpret **estimated cost/rows**, **actual time/rows**, **loops**, **filters**, and **buffers**.
- Compare a query plan before and after an index is introduced.
- Identify a slow operation and propose an evidence-based next step.

## Prerequisites

- Completed **Lab 00** (PostgreSQL available; database `paylab`; user `labuser`).
- Connected using **pgAdmin Query Tool** or `psql`.
- Basic SQL knowledge: `SELECT`, `WHERE`, `ORDER BY`, `GROUP BY`, indexes.

> **Execution convention:** Unless explicitly labeled *terminal*, run all SQL blocks **inside `paylab`**. Each block is independent unless a preceding setup step is specified. Timing and planner choices vary by device, cache, PostgreSQL version, and settings; compare the plans you actually obtain rather than expecting identical numbers.

---

## Part 1 — Inspect your environment 

```sql
SELECT current_database() AS database_name,
       current_user AS login_role,
       current_setting('server_version') AS pg_version;

SHOW shared_buffers;
SHOW work_mem;
SHOW random_page_cost;
```

**Expected:** Database = `paylab`. The other values depend on local configuration.

**Discuss:** `shared_buffers` is PostgreSQL's shared page cache; `work_mem` is the limit per sort/hash operation before spilling may occur (with details depending on the operation). Do not tune settings yet.

---

## Part 2 — Create a realistic transaction table

The data is synthetic, repeatable, and large enough to demonstrate several scan choices on common laptops.

### Step 2.1 — Build the table

```sql
DROP TABLE IF EXISTS lab01_transactions;

CREATE TABLE lab01_transactions (
    txn_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payer_account TEXT NOT NULL,
    payee_account TEXT NOT NULL,
    amount        NUMERIC(12,2) NOT NULL,
    status        TEXT NOT NULL,
    txn_ts        TIMESTAMP NOT NULL,
    channel       TEXT NOT NULL
);
```

### Step 2.2 — Insert 300,000 sample transactions

```sql
INSERT INTO lab01_transactions
    (payer_account, payee_account, amount, status, txn_ts, channel)
SELECT
    'u' || (g % 10000)::text || '@bank',
    'merchant' || (g % 2000)::text,
    ((g % 20000) + 50)::numeric / 10,
    CASE WHEN g % 20 = 0 THEN 'FAILED' ELSE 'SUCCESS' END,
    TIMESTAMP '2026-01-01 00:00:00' + (g % 7776000) * INTERVAL '1 second',
    CASE WHEN g % 4 = 0 THEN 'WEB' ELSE 'APP' END
FROM generate_series(1, 300000) AS g;

ANALYZE lab01_transactions;
```

> **Lower-resource laptops:** If 300,000 rows is too slow, substitute `100000` in `generate_series`, but observed timings and plan choices may differ.

### Step 2.3 — Validate the data

```sql
SELECT COUNT(*) AS total_transactions,
       COUNT(DISTINCT payer_account) AS distinct_payers,
       COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_transactions,
       MIN(txn_ts) AS earliest,
       MAX(txn_ts) AS latest
FROM lab01_transactions;
```

**Expected with 300,000 rows:** 300,000 transactions; 10,000 distinct payers; 15,000 failures. Date values begin in January 2026.

**Trainer question:** Is this an OLTP-like table? Which columns would an application commonly filter by?

---

## Part 3 — Your first plan: sequential scan (10 minutes)

### Step 3.1 — Estimated plan only

```sql
EXPLAIN
SELECT *
FROM lab01_transactions
WHERE payer_account = 'u1001@bank';
```

**Sample output:**

```text
                                      QUERY PLAN
--------------------------------------------------------------------------------------
 Gather  (cost=1000.00..5974.50 rows=30 width=55)
   Workers Planned: 2
   ->  Parallel Seq Scan on lab01_transactions  (cost=0.00..4971.50 rows=12 width=55)
         Filter: (payer_account = 'u1001@bank'::text)
```

**Execution Plan Explanation**

| Plan Component | Value | Explanation |
|---|---|---|
| Gather | Gather | Collects results from parallel workers |
| Startup Cost | 1000.00 | Estimated work before returning the first row |
| Total Cost | 5974.50 | Estimated total execution cost (not milliseconds) |
| Estimated Rows | 30 | PostgreSQL expects approximately 30 matching rows |
| Row Width | 55 | Estimated average row size is 55 bytes |
| Workers Planned | 2 | PostgreSQL plans to launch 2 parallel workers |
| Scan Type | Parallel Seq Scan | Workers scan different portions of the table |
| Scan Cost | 0.00..4971.50 | Estimated cost of scanning the table |
| Rows per Scan Participant | 12 | Estimated rows produced per parallel scan participant |
| Filter | `payer_account = 'u1001@bank'` | Only matching transactions are returned |

**Key Observations**

| Question | Answer |
|---|---|
| Is PostgreSQL using an index? | No |
| Is PostgreSQL scanning the table? | Yes, using a parallel sequential scan |
| Is parallel processing planned? | Yes, with 2 workers |
| Does PostgreSQL expect many matching rows? | No, approximately 30 |
| Is 5974.50 execution time in milliseconds? | No, it represents estimated planner cost |
| Do we know the actual execution time? | No, `EXPLAIN ANALYZE` is required |
| Can indexing improve this query? | Potentially, because the filter is selective |

### Step 3.2 — Execute and measure the same query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE payer_account = 'u1001@bank';
```

**Sample output:**

```text
                                                           QUERY PLAN
---------------------------------------------------------------------------------------------------------------------------------
 Gather  (cost=1000.00..5974.50 rows=30 width=55) (actual time=0.745..13.904 rows=30 loops=1)
   Workers Planned: 2
   Workers Launched: 2
   Buffers: shared hit=3409
   ->  Parallel Seq Scan on lab01_transactions  (cost=0.00..4971.50 rows=12 width=55) (actual time=0.200..8.610 rows=10 loops=3)
         Filter: (payer_account = 'u1001@bank'::text)
         Rows Removed by Filter: 99990
         Buffers: shared hit=3409
 Planning Time: 0.140 ms
 Execution Time: 13.937 ms
(10 rows)
```

The query scanned approximately 300,000 rows to find just 30 matching records, taking 13.937 ms.

**Execution Plan Analysis**

| Plan Component | Value and Explanation |
|---|---|
| Scan Type | Parallel Seq Scan — no index used |
| Workers | 2 launched + leader = 3 participants |
| Estimated Rows | 30 total |
| Actual Rows | 30 total |
| Rows Removed | 99,990 × 3 ≈ 299,970 |
| Shared Buffers Hit | 3,409 page accesses served from cache |
| Planning Time | 0.140 ms |
| Execution Time | 13.937 ms |

**Most Important Concept**

| Metric | Rows |
|---|---|
| Total rows examined | ~300,000 |
| Matching rows | 30 |
| Nonmatching rows | ~299,970 |
| Matching percentage | 0.01% |

> **Teaching point:** PostgreSQL scanned the entire table even though only 0.01% of rows matched. This is a strong candidate for testing a B-tree index.

---

## Part 4 — Read a plan bottom-up

### Step 4.1 — Run a query with a filter and aggregation

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT status, COUNT(*) AS txn_count, SUM(amount) AS total_amount
FROM lab01_transactions
WHERE channel = 'WEB'
GROUP BY status;
```

### Step 4.2 — Understand the plan tree

A plausible conceptual tree is:

```text
Aggregate / Finalize Aggregate       <-- produces grouped totals
  -> (possibly Sort or Gather)
       -> (possibly Partial Aggregate)
            -> Seq Scan / Parallel Seq Scan <-- reads and filters rows
```

**Read it in this order:**

1. Find the lowest scan node: how does PostgreSQL access the table?
2. Find its filter: which rows are retained?
3. Move upward: how are rows grouped and aggregates calculated?
4. Check each node's estimated vs. actual rows.
5. Check top-level planning and execution time.

> PostgreSQL may use `HashAggregate`, `GroupAggregate`, parallel aggregates, or other variations. The goal is to explain **your** tree, not to memorize one picture.

### Step 4.3 — Interpret the actual plan

This execution plan demonstrates the following flow, read from the bottom up:

```text
Parallel Seq Scan  →  Partial HashAggregate  →  Sort  →  Gather Merge  →  Finalize GroupAggregate
```

PostgreSQL scans approximately 300,000 transactions, filters 75,000 WEB transactions, and groups them into 2 status categories.

**Execution Plan Explanation**

| Component | Actual Value | Simple Explanation |
|---|---|---|
| Parallel Seq Scan | `rows=25000 loops=3` | Three participants each process approximately 25,000 matching rows |
| Filter | `channel = 'WEB'` | Only WEB transactions are selected |
| Rows Removed by Filter | 75,000 × 3 | Approximately 225,000 rows are rejected |
| Partial HashAggregate | `rows=2 loops=3` | Each participant groups its matching rows by status |
| Group Key | `status` | Groups transactions according to status |
| HashAggregate Memory | 24 kB | Small amount of memory for each participant's aggregation |
| Sort | quicksort, 25 kB | Sorts each participant's partial grouped results by status |
| Gather Merge | `rows=6` | Combines the 6 sorted partial results while preserving order |
| Finalize GroupAggregate | `rows=2` | Combines partial aggregates into 2 final groups |
| Shared Buffers Hit | 3,425 | Buffer accesses served from PostgreSQL's shared cache |
| Planning Time | 0.412 ms | Time to prepare the execution plan |
| Execution Time | 18.831 ms | Total execution time |

**Knowledge check:** If a scan passes 75,000 rows upward and an aggregate returns 2 rows, where did the other rows go?

---

## Part 5 — Index scan versus sequential scan

### Step 5.1 — Capture the baseline plan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE payer_account = 'u1001@bank';
```

**Sample output:**

```text
                                                           QUERY PLAN
---------------------------------------------------------------------------------------------------------------------------------
 Gather  (cost=1000.00..5974.50 rows=30 width=55) (actual time=0.568..12.886 rows=30 loops=1)
   Workers Planned: 2
   Workers Launched: 2
   Buffers: shared hit=3409
   ->  Parallel Seq Scan on lab01_transactions  (cost=0.00..4971.50 rows=12 width=55) (actual time=0.578..7.797 rows=10 loops=3)
         Filter: (payer_account = 'u1001@bank'::text)
         Rows Removed by Filter: 99990
         Buffers: shared hit=3409
 Planning Time: 0.120 ms
 Execution Time: 12.915 ms
(10 rows)
```

Copy the displayed plan into your lab notes.

### Step 5.2 — Create a B-tree index

```sql
CREATE INDEX idx_lab01_payer
ON lab01_transactions (payer_account);

ANALYZE lab01_transactions;
```

### Step 5.3 — Re-run the identical query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE payer_account = 'u1001@bank';
```

**Sample output:**

```text
                                                        QUERY PLAN
--------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on lab01_transactions  (cost=4.66..116.59 rows=30 width=55) (actual time=0.081..0.179 rows=30 loops=1)
   Recheck Cond: (payer_account = 'u1001@bank'::text)
   Heap Blocks: exact=30
   Buffers: shared hit=30 read=3
   ->  Bitmap Index Scan on idx_lab01_payer  (cost=0.00..4.65 rows=30 width=0) (actual time=0.067..0.067 rows=30 loops=1)
         Index Cond: (payer_account = 'u1001@bank'::text)
         Buffers: shared read=3
 Planning:
   Buffers: shared hit=27 read=1
 Planning Time: 0.373 ms
 Execution Time: 0.203 ms
(11 rows)
```

**Likely outcome:** The planner may choose `Bitmap Index Scan` + `Bitmap Heap Scan`, or `Index Scan`, because the predicate selects roughly 30 rows out of 300,000. Compare actual results; PostgreSQL can still select a sequential scan in some environments.

| Metric | Before index | After index |
|---|---|---|
| Scan strategy | Parallel Seq Scan | Bitmap Index Scan + Bitmap Heap Scan |
| Estimated rows | 30 | 30 |
| Actual rows | 30 | 30 |
| Shared blocks hit/read | hit=3,409, read=0 | hit=30, read=3 |
| Execution time (ms) | 12.915 | 0.203 |

**Guided questions:**

- Does the index avoid scanning most of the table?
- What extra work is required to fetch columns not stored in the index?
- Is the improvement larger or smaller on repeated runs? Why might caching matter?

> **Important:** Do not conclude that an index always speeds up SQL. Maintaining an index has write and storage costs, and selective access differs from reading most of a table.

---

## Part 6 — Selectivity: why the same index is not always used

A query returning nearly every row may still prefer a full scan:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE status IN ('SUCCESS', 'FAILED');
```

Only about 5% of records have `FAILED` status:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE status = 'FAILED';
```

Now add an index:

```sql
CREATE INDEX idx_lab01_status
ON lab01_transactions (status);

ANALYZE lab01_transactions;
```

Repeat the two queries. The first normally has little reason to use the index because the condition accepts every row. The second **may or may not** use it; scan choice depends on table size, row width, estimates, and cost assumptions.

**Takeaway:** A useful index supports an access pattern. The presence of an index does not oblige PostgreSQL to use it.

---

## Part 7 — Sorting and `ORDER BY`

### Step 7.1 — Find the sort node

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, amount, txn_ts
FROM lab01_transactions
WHERE status = 'FAILED'
ORDER BY amount DESC
LIMIT 20;
```

Inspect whether the plan has a `Sort` node. If present, check `Sort Key`, `Sort Method`, and memory used. A `top-N heapsort` can appear for `LIMIT`, depending on the plan.

### Step 7.2 — Create an ordering-friendly index

```sql
CREATE INDEX idx_lab01_status_amount_desc
ON lab01_transactions (status, amount DESC);

ANALYZE lab01_transactions;
```

Re-run Step 7.1. Does the planner use the index to satisfy both the equality predicate on `status` and the requested order on `amount`?

**Discuss:** A matching index may avoid an explicit sort; it does not guarantee that the planner uses the index.

---

## Part 8 — Recognize inaccurate row estimates

This comparison illustrates the meaning of **estimation error**.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab01_transactions
WHERE payer_account = 'u1001@bank'
  AND status = 'FAILED';
```

**Check:**

- The estimated row count at the scan node.
- The measured row count.
- Whether the planner assumed the two predicates were independent.
- Whether a difference between estimates and reality matters to execution time.

A mismatch is not automatically a performance defect, especially with small absolute row counts. In later labs, we examine stale statistics, correlated columns, and ways to improve estimates.

---

## Part 9 — Independent exercises

Complete these without reading the answer key first.

### Exercise A — Find the costliest operation

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT payee_account, COUNT(*) AS txn_count
FROM lab01_transactions
WHERE txn_ts >= TIMESTAMP '2026-02-01'
  AND txn_ts < TIMESTAMP '2026-03-01'
GROUP BY payee_account
ORDER BY txn_count DESC
LIMIT 10;
```

- Identify the scan, aggregate, and sort/ordering stages.
- What operation reads the most rows?
- Which node takes the most time? Be careful: parent node times often include child work.
- Propose one index worth testing in a later tuning lab.

### Exercise B — Compare narrow and broad filters

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM lab01_transactions WHERE payer_account = 'u42@bank';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM lab01_transactions WHERE channel = 'APP';
```

- Which predicate is more selective?
- Which query uses fewer shared buffer accesses?
- Why might the planner make different scan decisions?

### Exercise C — Estimate versus actual

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab01_transactions
WHERE amount > 1500;
```

- Write down the planner estimate at the underlying scan.
- Write down actual rows from that scan.
- Distinguish rows emitted by the scan from the final `COUNT(*)` output (one row).

---

## Part 10 — Trainer answer key and teaching notes

**Part 2 validation:** With the full dataset, `300000` rows, `10000` distinct payer accounts, and `15000` failed transactions.

**Part 3:** Without the payer index, a sequential scan is a reasonable expected plan. Typically 30 rows match a particular payer; an index created later is likely to help.

**Part 4:** Aggregation compresses many input rows into grouped results; the rows are summarized, not necessarily discarded by a filter.

**Part 5:** After indexing, PostgreSQL can use direct or bitmap index access. Index lookup is usually compelling for ~30 matches out of 300,000, but exact plans and timing must be observed.

**Part 6:** An unselective predicate often favors a sequential scan because fetching many heap rows through an index can cost more.

**Part 7:** `(status, amount DESC)` can serve a query with `status = 'FAILED'`, `ORDER BY amount DESC`, `LIMIT 20`; investigate whether the standalone sort disappears.

**Exercise A:** Expect a large input scan and then grouping and top-N ordering. A B-tree on `txn_ts` may be worth testing **if the date range is selective enough**; this exercise does not prove it is beneficial.

**Exercise B:** The payer predicate matches about 30 rows; `channel = 'APP'` matches approximately 225,000. Narrow equality is much more index-friendly than broad channel filtering.

**Exercise C:** Final aggregate `COUNT(*)` emits **one** row. The filtered scan has a much larger row count. Learners should not confuse the two nodes.

### Instructor demonstration suggestions

1. Project the same query twice: estimated-only plan, then measured plan.
2. Highlight `cost`, `rows`, `actual time`, `loops`, and `Buffers` one at a time.
3. Show the query **before and after** indexing; use the same SQL text.
4. Make learners verbalize the access path rather than judge only execution milliseconds.
5. Close by asking: “What evidence should we collect before rewriting SQL?”

### Important safety and accuracy notes

- `EXPLAIN` alone **does not execute** the query; `EXPLAIN ANALYZE` **does**. Be careful with `UPDATE`, `DELETE`, and `INSERT` (use a rollback-only transaction when experimenting).
- `Execution Time` varies with CPU load, concurrent activity, caching, and query planner choices. Run comparisons repeatedly and interpret them cautiously.
- PostgreSQL's estimated **cost** is a planning metric, **not elapsed time**.
- `BUFFERS` reports PostgreSQL buffer activity, not direct per-query disk latency measurements.
- `EXPLAIN ANALYZE` has some instrumentation overhead. Always interpret timing relatively and in context.

---

## Completion checklist

- [ ] Connected to `paylab`.
- [ ] Created and analyzed `lab01_transactions`.
- [ ] Explained the output of `EXPLAIN (ANALYZE, BUFFERS)`.
- [ ] Captured a baseline plan before indexing.
- [ ] Created indexes and compared actual plans.
- [ ] Identified scan, filter, sort, and aggregate nodes.
- [ ] Completed Exercises A, B, and C.

**Next lab:** **Lab 02 — Indexing Strategies and Selectivity** (composite indexes, index order, partial indexes, covering indexes, and their tradeoffs).
