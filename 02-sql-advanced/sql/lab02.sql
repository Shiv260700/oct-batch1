-- =====================================================================
-- Lab 02 — Index Design
-- Story: u1000@bank's support screen is fast now (Lab 01). New requests
--        arrive: "latest 10 payments", "payments on one day",
--        "failed payments queue", "search customer by name".
--        Which index for which question?
--
-- Run one step at a time (copy into psql), or the whole file:
--     \i sql/lab02.sql
-- Guide: labs/lab-02-index-design.md
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — Clean start
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Keep plans simple for the whole lab: no parallel workers.
SET max_parallel_workers_per_gather = 0;

-- ---------------------------------------------------------------------
-- STEP 1 — Selectivity: how many rows does each filter keep?
-- ---------------------------------------------------------------------
SELECT status, count(*) AS payments,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_table
FROM transactions
GROUP BY status
ORDER BY payments DESC;

SELECT payer_account, count(*) AS payments
FROM transactions
WHERE payer_account IN ('u1000@bank', 'u42@bank')
GROUP BY payer_account;

-- ---------------------------------------------------------------------
-- STEP 2 — Same index, different number of rows
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_payer ON transactions (payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE payer_account = 'u1000@bank';   -- 103 rows

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE payer_account = 'u42@bank';     -- 10,216 rows

-- ---------------------------------------------------------------------
-- STEP 3 — When the planner ignores an index
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_status ON transactions (status);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'PENDING';    -- 1% of rows

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'SUCCESS';    -- 94% of rows

-- Force the index (for learning only) and compare:
BEGIN;
SET LOCAL enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions WHERE status = 'SUCCESS';
ROLLBACK;

-- ---------------------------------------------------------------------
-- STEP 4 — Composite index: "latest 10 payments" of a customer
-- ---------------------------------------------------------------------
-- With only the single-column payer index:
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount, status
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC
LIMIT 10;

-- Index on (who, when): equality column first, then the ORDER BY column
CREATE INDEX idx_txn_payer_ts ON transactions (payer_account, txn_ts DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount, status
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC
LIMIT 10;

-- Our story customer, with the right index (compare with Step 5)
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount, status
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC
LIMIT 10;

-- ---------------------------------------------------------------------
-- STEP 5 — Column order matters
-- Try the "wrong" order, inside a transaction so we can undo it.
-- ---------------------------------------------------------------------
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
ROLLBACK;     -- the two good indexes are back, the wrong one is gone

-- ---------------------------------------------------------------------
-- STEP 6 — Don't wrap the indexed column in a function (SARGable)
-- Question: how many payments on 15 March 2026?
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_ts ON transactions (txn_ts);

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts::date = DATE '2026-03-15';

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15'
  AND txn_ts <  TIMESTAMP '2026-03-16';

-- ---------------------------------------------------------------------
-- STEP 7 — Expression index: search a customer by name, any case
-- ---------------------------------------------------------------------
CREATE INDEX idx_acc_name ON accounts (holder_name);

EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name, city
FROM accounts
WHERE lower(holder_name) = 'ravi kumar';

CREATE INDEX idx_acc_name_lower ON accounts (lower(holder_name));

EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name, city
FROM accounts
WHERE lower(holder_name) = 'ravi kumar';

-- ---------------------------------------------------------------------
-- STEP 8 — Partial index: the "failed payments" queue
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount, txn_ts
FROM transactions
WHERE status = 'FAILED'
ORDER BY txn_ts DESC
LIMIT 20;

CREATE INDEX idx_txn_failed_ts ON transactions (txn_ts DESC)
WHERE status = 'FAILED';

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, payer_account, amount, txn_ts
FROM transactions
WHERE status = 'FAILED'
ORDER BY txn_ts DESC
LIMIT 20;

-- Size: partial index vs a full index on the same column
SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexrelname IN ('idx_txn_ts', 'idx_txn_failed_ts');

-- ---------------------------------------------------------------------
-- STEP 9 — Covering index: answer from the index alone
-- ---------------------------------------------------------------------
-- Needs only txn_ts and amount. Our (payer, txn_ts) index lacks amount.
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC;

CREATE INDEX idx_txn_payer_ts_amt ON transactions (payer_account, txn_ts DESC)
INCLUDE (amount);

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC;

-- ---------------------------------------------------------------------
-- STEP 10 — Why "Heap Fetches" can appear: the visibility map
-- ---------------------------------------------------------------------
-- Touch u1000's rows, then undo. The pages are no longer "all-visible".
BEGIN;
UPDATE transactions SET amount = amount WHERE payer_account = 'u1000@bank';
ROLLBACK;

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC;

VACUUM transactions;    -- marks pages all-visible again

EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_ts, amount
FROM transactions
WHERE payer_account = 'u1000@bank'
ORDER BY txn_ts DESC;

-- ---------------------------------------------------------------------
-- STEP 11 — BRIN: a tiny index for time-ordered data
-- ---------------------------------------------------------------------
-- Rows were inserted in time order: check the correlation (1 = perfect)
SELECT attname, correlation
FROM pg_stats
WHERE tablename = 'transactions' AND attname IN ('txn_ts', 'payer_account');

CREATE INDEX idx_txn_ts_brin ON transactions USING brin (txn_ts);

SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexrelname IN ('idx_txn_ts', 'idx_txn_ts_brin');

-- Hide the B-tree for a moment to see BRIN at work
BEGIN;
DROP INDEX idx_txn_ts;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15'
  AND txn_ts <  TIMESTAMP '2026-03-16';
ROLLBACK;

-- ---------------------------------------------------------------------
-- STEP 12 — Indexes are not free
-- ---------------------------------------------------------------------
-- 12a. How much space do all these indexes take?
SELECT indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE relname = 'transactions'
ORDER BY pg_relation_size(indexrelid) DESC;

SELECT pg_size_pretty(pg_relation_size('transactions')) AS table_size,
       pg_size_pretty(pg_indexes_size('transactions'))  AS all_indexes_size;

-- 12b. Write cost: load 50,000 payments into two empty copies of the table
--      load_plain   : no indexes at all
--      load_indexed : the same indexes transactions has right now
CREATE TABLE load_plain   (LIKE transactions);
CREATE TABLE load_indexed (LIKE transactions INCLUDING INDEXES);

EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO load_plain   SELECT * FROM transactions WHERE txn_id <= 50000;

EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO load_indexed SELECT * FROM transactions WHERE txn_id <= 50000;

SELECT 'load_plain'   AS copy, pg_size_pretty(pg_total_relation_size('load_plain'))   AS total_size
UNION ALL
SELECT 'load_indexed',          pg_size_pretty(pg_total_relation_size('load_indexed'));

DROP TABLE load_plain;
DROP TABLE load_indexed;

-- =====================================================================
-- TRY IT YOURSELF (answers in trainer/lab-02-answers.md)
-- =====================================================================
-- T1. Ops asks: "top 5 biggest payments of u1000@bank".
--     Design an index so the plan has no Sort node. Prove it with EXPLAIN.
--
-- T2. Is   WHERE channel = 'WEB'   (15% of rows) a good index candidate?
--     Create the index, run EXPLAIN (ANALYZE, BUFFERS), and explain the plan.
--
-- T3. Rewrite to be index-friendly (index on txn_ts exists):
--       SELECT count(*) FROM transactions
--       WHERE date_trunc('month', txn_ts) = TIMESTAMP '2026-02-01';
--
-- T4. Make this fast with a partial index:
--       SELECT * FROM transactions
--       WHERE status = 'PENDING' AND payee_account IS NULL;
