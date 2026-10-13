# Lab 02 — Indexing Strategies and Selectivity in PostgreSQL

**Course:** Advanced SQL — PostgreSQL  
**Lab:** 02  
**Level:** Intermediate to Advanced  
**Database:** `paylab`  
**Goal:** Choose and validate indexes using query patterns, cardinality, selectivity, and actual PostgreSQL execution plans.

## Learning objectives

After completing this lab, you can:

- Explain why an index does **not** automatically make every query faster.
- Evaluate cardinality and filter selectivity before designing an index.
- Compare B-tree indexes, multicolumn indexes, partial indexes, expression indexes, covering indexes, and BRIN indexes.
- Recognize `Seq Scan`, `Index Scan`, `Bitmap Index Scan`, `Bitmap Heap Scan`, and `Index Only Scan`.
- Analyze costs, actual execution metrics, shared buffers, and index storage overhead.
- Build indexes for realistic queries and defend the design using evidence.

## Prerequisites

- PostgreSQL running locally or in Docker; `paylab` accessible through pgAdmin or `psql`.
- Lab 01's `lab01_transactions` table populated with sample transactions.
- Permission to create tables and indexes within `paylab`.

> **Execution guidance:** Run all SQL in the `paylab` database unless a shell command is explicitly shown. Execute each step sequentially. **Do not compare absolute execution times across machines.** PostgreSQL may choose different plans depending on its statistics, table size, version, hardware and caching. `EXPLAIN (ANALYZE, BUFFERS)` actually executes a query. Use it with care for `UPDATE`, `DELETE` and `INSERT`.

---

## Exercise 1 — Prepare a clean lab table

Lab 01 introduced indexes of its own. Make a *copy* of its data so existing indexes do not interfere with today's experiments. `CREATE TABLE ... AS` does not copy the source table's indexes or constraints.

```sql
-- Confirm that the input table exists.
SELECT to_regclass('public.lab01_transactions') AS source_table;

-- Stop here if the result is NULL; complete Lab 01 setup first.
DROP TABLE IF EXISTS lab02_transactions;

CREATE TABLE lab02_transactions AS
SELECT * FROM lab01_transactions;

ANALYZE lab02_transactions;

SELECT COUNT(*) AS total_rows,
       MIN(txn_ts) AS first_transaction,
       MAX(txn_ts) AS last_transaction
FROM lab02_transactions;
```

**Expected:** `300000` rows when Lab 01 used its full dataset. This lab table has no indexes initially. Lab 01's original table is preserved.

Verify the absence of indexes:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'lab02_transactions';
```

**Expected:** Zero rows.

---

## Exercise 2 — Understand cardinality and selectivity

- **Cardinality:** Number of distinct values in a column.
- **Selectivity:** Fraction of table rows satisfying a condition; a *smaller* fraction often makes an index more attractive.
- A predicate matching nearly every row often favors a sequential scan.

Inspect the distribution:

```sql
SELECT
    COUNT(*) AS rows_total,
    COUNT(DISTINCT payer_account) AS distinct_payers,
    COUNT(DISTINCT status) AS distinct_statuses,
    COUNT(DISTINCT channel) AS distinct_channels,
    COUNT(DISTINCT payee_account) AS distinct_payees
FROM lab02_transactions;

SELECT status, COUNT(*) AS rows_matched,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM lab02_transactions), 2)
           AS selectivity_percent
FROM lab02_transactions
GROUP BY status
ORDER BY rows_matched DESC;

SELECT payer_account, COUNT(*) AS rows_matched
FROM lab02_transactions
WHERE payer_account = 'u1001@bank'
GROUP BY payer_account;
```

**Expected with Lab 01's 300,000-row dataset:**

- Approximately `10000` unique payers, each with `30` rows.
- `FAILED` has `15000` rows (5%); `SUCCESS` has `285000` (95%).
- `channel` contains `APP` and `WEB` and is low-cardinality.

**Discussion:** Would you index `payer_account`, `status`, or `channel` first for point lookups? What changes if the application frequently fetches all `FAILED` transactions?

Check the planner's statistics after `ANALYZE`:

```sql
SELECT attname, n_distinct, most_common_vals, most_common_freqs
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename = 'lab02_transactions'
  AND attname IN ('payer_account', 'status', 'channel');
```

`n_distinct` can be a negative fraction representing an estimate relative to table size; it is not always a literal distinct-value count.

---

## Exercise 3 — B-tree: selective equality vs broad filters

### Step 3.1 — Establish the baseline

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank';
```

**Look for:** `Seq Scan`, `Rows Removed by Filter`, estimated vs actual rows, shared buffers, and `Execution Time`.

### Step 3.2 — Create a B-tree index and retest

```sql
CREATE INDEX idx_lab02_payer
ON lab02_transactions (payer_account);

ANALYZE lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank';
```

**Likely observation:** `Bitmap Heap Scan` + `Bitmap Index Scan`, or `Index Scan`, with fewer heap pages read than a full-table scan. The specific plan is not guaranteed.

### Step 3.3 — Compare a nonselective predicate

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE payer_account <> 'u1001@bank';
```

**Expected concept:** A filter matching almost all rows often retains a sequential scan even when the column is indexed.

**Checkpoint:** Explain why a smaller *selectivity fraction* can be more favorable for an index than a predicate matching most rows.

---

## Exercise 4 — Composite B-tree index and column order

**Application request:** List a payer's most recent transactions.

### Step 4.1 — Baseline

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

Look for the need to sort matching rows.

### Step 4.2 — Create a query-aligned composite index

```sql
CREATE INDEX idx_lab02_payer_ts_desc
ON lab02_transactions (payer_account, txn_ts DESC);

ANALYZE lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

**What to look for:** An ordered index scan may serve both the equality filter and the `ORDER BY ... LIMIT`, avoiding a separate sort.

### Step 4.3 — Evaluate the leading-column rule

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts
FROM lab02_transactions
WHERE txn_ts >= TIMESTAMP '2026-03-01'
  AND txn_ts < TIMESTAMP '2026-03-02';
```

**Discuss:** The index begins with `payer_account`, but this query filters only on `txn_ts`. PostgreSQL generally cannot use this index as efficiently as one beginning with `txn_ts` for this predicate. Depending on version and statistics, index skip-scan or other planner choices may be possible; read the actual plan.

### Step 4.4 — Validate the alternative

```sql
CREATE INDEX idx_lab02_txn_ts
ON lab02_transactions (txn_ts);

ANALYZE lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts
FROM lab02_transactions
WHERE txn_ts >= TIMESTAMP '2026-03-01'
  AND txn_ts < TIMESTAMP '2026-03-02';
```

**Checkpoint:** Describe which predicates are supported well by `(payer_account, txn_ts DESC)` and which are supported better by `(txn_ts)`.

---

## Exercise 5 — Partial index for an important minority

Assume operations frequently searches for **failed** payments. A partial index stores only rows satisfying its predicate.

### Step 5.1 — Baseline

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts
FROM lab02_transactions
WHERE status = 'FAILED'
  AND payer_account = 'u1000@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

> **Dataset note:** In Lab 01's deterministic dataset, payers with IDs divisible by 20 (such as `u1000@bank`) have failed records, while others may have none. This matters when choosing test values.

### Step 5.2 — Create a partial index

```sql
CREATE INDEX idx_lab02_failed_payer_ts
ON lab02_transactions (payer_account, txn_ts DESC)
WHERE status = 'FAILED';

ANALYZE lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts
FROM lab02_transactions
WHERE status = 'FAILED'
  AND payer_account = 'u1000@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

Inspect the index size:

```sql
SELECT indexrelid::regclass AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_index
WHERE indrelid = 'lab02_transactions'::regclass
ORDER BY indexrelid::regclass::text;
```

**Discuss:** A partial index is smaller because it excludes `SUCCESS` rows. It can be used only when PostgreSQL can recognize that the query's predicate implies the index predicate. Some prepared/parameterized queries may not use a partial index if implication cannot be established at planning time.

---

## Exercise 6 — Expression index: make a case-insensitive lookup indexable

**Application request:** Search a payer ID regardless of case.

### Step 6.1 — Baseline

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE LOWER(payer_account) = LOWER('U1001@BANK');
```

Even with the ordinary `payer_account` index, the expression `LOWER(payer_account)` generally requires a matching expression index for efficient direct lookup.

### Step 6.2 — Create and verify

```sql
CREATE INDEX idx_lab02_payer_lower
ON lab02_transactions (LOWER(payer_account));

ANALYZE lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE LOWER(payer_account) = LOWER('U1001@BANK');
```

**Checkpoint:** The query expression and indexed expression should align. An expression index introduces extra maintenance work on writes.

---

## Exercise 7 — Covering index and index-only scans

**Application request:** Frequently fetch the latest `txn_ts` and `amount` values for a payer, without needing the full row.

### Step 7.1 — Create a covering index

```sql
CREATE INDEX idx_lab02_payer_ts_cover
ON lab02_transactions (payer_account, txn_ts DESC)
INCLUDE (amount);

-- Makes all-visible page information more likely to be available
-- for a stable training dataset. VACUUM cannot run inside a transaction block.
VACUUM (ANALYZE) lab02_transactions;

EXPLAIN (ANALYZE, BUFFERS)
SELECT payer_account, txn_ts, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

**Look for:** `Index Only Scan` and `Heap Fetches`. PostgreSQL may still choose another suitable index because earlier experiments created overlapping indexes. An index-only scan is possible only if all referenced columns are available in the index and visibility checks permit it; even an `Index Only Scan` can perform heap fetches.

### Step 7.2 — Optional controlled comparison

To demonstrate the covering index's behavior without overlapping competition, inspect a new *copy* with a single index:

```sql
DROP TABLE IF EXISTS lab02_cover_demo;
CREATE TABLE lab02_cover_demo AS
SELECT payer_account, txn_ts, amount
FROM lab02_transactions;

CREATE INDEX idx_lab02_cover_demo
ON lab02_cover_demo (payer_account, txn_ts DESC)
INCLUDE (amount);

VACUUM (ANALYZE) lab02_cover_demo;

EXPLAIN (ANALYZE, BUFFERS)
SELECT payer_account, txn_ts, amount
FROM lab02_cover_demo
WHERE payer_account = 'u1001@bank'
ORDER BY txn_ts DESC
LIMIT 10;
```

**Discuss:** `INCLUDE` columns are stored in leaf tuples but not part of the B-tree search key. Covering indexes may improve selected reads but cost extra space and write work.

---

## Exercise 8 — BRIN for large, physically ordered timestamp data

A BRIN index summarizes ranges of physical pages. It is often useful for very large tables whose data values correlate with physical order, such as append-only event data.

**Important:** The original Lab 01 sample isn't physically sorted by timestamp. Build a separate timestamp-ordered demonstration table to avoid a misleading comparison.

```sql
DROP TABLE IF EXISTS lab02_brin_demo;

CREATE TABLE lab02_brin_demo AS
SELECT g AS event_id,
       TIMESTAMP '2026-01-01' + g * INTERVAL '1 minute' AS event_ts,
       (g % 100)::integer AS payload
FROM generate_series(1, 500000) AS g;

ANALYZE lab02_brin_demo;

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab02_brin_demo
WHERE event_ts >= TIMESTAMP '2026-08-01'
  AND event_ts < TIMESTAMP '2026-08-02';

CREATE INDEX idx_lab02_brin_ts
ON lab02_brin_demo USING BRIN (event_ts);

ANALYZE lab02_brin_demo;

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab02_brin_demo
WHERE event_ts >= TIMESTAMP '2026-08-01'
  AND event_ts < TIMESTAMP '2026-08-02';

SELECT pg_size_pretty(pg_relation_size('idx_lab02_brin_ts')) AS brin_size;
```

**Expected concept:** A BRIN index is compact and may help skip unrelated page ranges; its scans are generally lossy and may recheck rows. Your plan can still choose a sequential scan if the planner estimates that as cheaper.

**Optional size comparison:**

```sql
CREATE INDEX idx_lab02_brin_demo_btree
ON lab02_brin_demo (event_ts);

SELECT relname AS index_name,
       pg_size_pretty(pg_relation_size(oid)) AS index_size
FROM pg_class
WHERE oid IN ('idx_lab02_brin_ts'::regclass,
              'idx_lab02_brin_demo_btree'::regclass)
ORDER BY relname;
```

**Checkpoint:** Explain when a B-tree might outperform BRIN for targeted lookups, even though BRIN uses far less storage.

---

## Exercise 9 — Index cost and maintenance

Indexes speed up some reads but are not free. They consume disk space and add work to inserts, updates and deletes.

### Step 9.1 — Check table and index sizes

```sql
SELECT
    pg_size_pretty(pg_relation_size('lab02_transactions')) AS table_bytes,
    pg_size_pretty(pg_indexes_size('lab02_transactions')) AS all_indexes_bytes,
    pg_size_pretty(pg_total_relation_size('lab02_transactions')) AS total_bytes;
```

### Step 9.2 — Find overlapping indexes

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'lab02_transactions'
ORDER BY indexname;
```

**Discuss:** `idx_lab02_payer`, `idx_lab02_payer_ts_desc` and `idx_lab02_payer_ts_cover` overlap for some query patterns. This does not automatically mean one is redundant: compare actual workloads, sort requirements, index-only scan behavior, write volume, and storage costs before removing any index.

### Step 9.3 — View usage counters

```sql
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'lab02_transactions'
ORDER BY indexrelname;
```

**Caution:** Statistics accumulate over time and may be reset. Index usage counts alone are not sufficient evidence to drop an index, especially on a new training database.

---

## Independent practice challenges

Attempt each challenge before looking at the suggested answer.

**Challenge A — Top payments by payer**  
Write a query to fetch the 15 highest-value payments by a specific payer. Recommend an index that can support both the payer filter and descending amount order. Confirm with `EXPLAIN (ANALYZE, BUFFERS)`.

**Challenge B — Failed transaction queue**  
Find the 20 most recent failed transactions for payer `u1000@bank`. Explain why a partial index could be helpful, and how the query must match its predicate.

**Challenge C — Daily transaction reporting**  
Write a query that counts transactions during a single day. Test the existing timestamp B-tree; explain why a half-open date range is preferable to applying `DATE()` to `txn_ts` for a normal timestamp index.

**Challenge D — Index review**  
Identify two potentially overlapping indexes from this lab. Describe the read, write and storage trade-offs of retaining both.

---

## Suggested solutions and trainer discussion

### Solution A

```sql
CREATE INDEX idx_lab02_payer_amount_desc
ON lab02_transactions (payer_account, amount DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount
FROM lab02_transactions
WHERE payer_account = 'u1001@bank'
ORDER BY amount DESC
LIMIT 15;
```

**Answer:** Equality on the first index column plus sorted access through the second column can remove an explicit sorting step.

### Solution B

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, txn_ts
FROM lab02_transactions
WHERE status = 'FAILED'
  AND payer_account = 'u1000@bank'
ORDER BY txn_ts DESC
LIMIT 20;
```

**Answer:** `idx_lab02_failed_payer_ts` contains only failed rows and orders timestamps within each payer. Whether the planner selects it still depends on its cost model.

### Solution C

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab02_transactions
WHERE txn_ts >= TIMESTAMP '2026-03-01'
  AND txn_ts < TIMESTAMP '2026-03-02';
```

**Answer:** Half-open timestamp boundaries handle time-of-day correctly and can align with an ordinary index on `txn_ts`.

### Solution D

**Answer:** The single-column `payer_account` index may overlap with composite indexes beginning with `payer_account`. Don't drop it solely on that observation: measure key production queries and account for write load and index size.

---

## Troubleshooting

- **`relation "lab01_transactions" does not exist`:** Run Lab 01's data setup first, then return to Exercise 1.
- **`permission denied for schema public`:** Connect with a user permitted to create tables and indexes in the lab schema.
- **`VACUUM cannot run inside a transaction block`:** Run the `VACUUM` statement separately, outside `BEGIN`/`COMMIT` or a tool that wraps multiple statements in one transaction.
- **PostgreSQL still chooses `Seq Scan`:** Normal on small or unselective queries. Verify row count, `ANALYZE` statistics, index definition and predicate before judging the index.
- **An `Index Only Scan` still has `Heap Fetches`:** Visibility information requires consulting heap pages. `VACUUM` may help for a stable test table.
- **Execution times fluctuate:** Warm caches, other workloads and planning choices affect timings. Compare plans and buffer activity alongside elapsed time.
- **`CREATE INDEX` reports that the name exists:** The lab has been run before. To start over, rerun Exercise 1, which drops only `lab02_transactions`; for the optional demo tables, rerun their explicit `DROP TABLE` blocks.

## Completion checklist

- [ ] Copied the Lab 01 data to a clean lab table.
- [ ] Compared high- and low-selectivity predicates.
- [ ] Demonstrated B-tree scans with execution plans.
- [ ] Created a multicolumn index for `WHERE` + `ORDER BY`.
- [ ] Tested a partial index on failed payments.
- [ ] Created and tested an expression index.
- [ ] Demonstrated a covering index and evaluated heap fetches.
- [ ] Compared BRIN with B-tree for timestamp-ordered records.
- [ ] Reviewed index storage cost and overlapping indexes.
- [ ] Solved the independent challenges.

## Key takeaways

1. **Start with the workload and execution plan, not with a list of columns to index.**
2. Selective predicates are often good index candidates; broad predicates may not be.
3. Column order matters in composite indexes, especially when combining equality, range, and sorting operations.
4. Partial, expression, and covering indexes solve different problems and should be justified individually.
5. More indexes may increase storage and write overhead; **prove the benefit** before keeping an index.

**Next lab:** Lab 03 — Join Optimization and Query Tuning.
