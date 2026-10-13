-- =====================================================================
-- Lab 01 — Reading an Execution Plan
-- Story: customer u1000@bank asks "show me my payments". Why is it slow?
--
-- Run one step at a time: copy a step into psql, or run the whole file:
--     \i sql/lab01.sql
-- Guide: labs/lab-01-reading-plans.md
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — Clean start
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Keep the first plans simple: one worker, no parallel query.
-- (We switch parallel query back on in Step 9.)
SET max_parallel_workers_per_gather = 0;

-- ---------------------------------------------------------------------
-- STEP 1 — How big is the table?
-- ---------------------------------------------------------------------
SELECT count(*) AS total_rows FROM transactions;

SELECT relpages                                    AS pages_8kb,
       pg_size_pretty(pg_relation_size('transactions')) AS table_size,
       round(reltuples / relpages)                 AS rows_per_page
FROM pg_class
WHERE relname = 'transactions';

-- ---------------------------------------------------------------------
-- STEP 2 — EXPLAIN: the plan only (the query is NOT run)
-- ---------------------------------------------------------------------
EXPLAIN
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';

-- ---------------------------------------------------------------------
-- STEP 3 — Where does the cost number come from?
-- ---------------------------------------------------------------------
SHOW seq_page_cost;      -- price of reading one page in order
SHOW cpu_tuple_cost;     -- price of handling one row
SHOW cpu_operator_cost;  -- price of one check, e.g. payer_account = '...'

SELECT 12606 * 1.0        -- pages  x seq_page_cost
     + 1000000 * 0.01     -- rows   x cpu_tuple_cost
     + 1000000 * 0.0025   -- checks x cpu_operator_cost
       AS total_cost;

-- ---------------------------------------------------------------------
-- STEP 4 — EXPLAIN ANALYZE: run it and measure
-- ---------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';

-- ---------------------------------------------------------------------
-- STEP 5 — BUFFERS: how many pages did it touch?
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';

-- ---------------------------------------------------------------------
-- STEP 6 — A plan with three nodes: read it bottom-up
-- Question: how many FAILED payments per channel?
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT channel, count(*) AS failed
FROM transactions
WHERE status = 'FAILED'
GROUP BY channel
ORDER BY failed DESC;

-- ---------------------------------------------------------------------
-- STEP 7 — Your first Index Scan (the primary key already has an index)
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE txn_id = 500000;

-- ---------------------------------------------------------------------
-- STEP 8 — Add an index for the story query and compare
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_payer ON transactions (payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM transactions
WHERE payer_account = 'u1000@bank';

-- ---------------------------------------------------------------------
-- STEP 9 — Parallel query: several workers share one scan
-- ---------------------------------------------------------------------
RESET max_parallel_workers_per_gather;    -- back to the default (2)

EXPLAIN (ANALYZE, BUFFERS)
SELECT channel, count(*) AS failed
FROM transactions
WHERE status = 'FAILED'
GROUP BY channel
ORDER BY failed DESC;

-- ---------------------------------------------------------------------
-- STEP 10 — Safety: EXPLAIN ANALYZE really runs the statement
-- ---------------------------------------------------------------------
BEGIN;

EXPLAIN ANALYZE
UPDATE transactions SET status = 'FAILED'
WHERE txn_id = 1;

SELECT txn_id, status FROM transactions WHERE txn_id = 1;   -- changed!

ROLLBACK;                                                   -- undo it

SELECT txn_id, status FROM transactions WHERE txn_id = 1;   -- back to normal

-- =====================================================================
-- TRY IT YOURSELF (answers in trainer/lab-01-answers.md)
-- =====================================================================
-- T1. Run EXPLAIN (ANALYZE, BUFFERS) for payer 'u42@bank' (a busy payer).
--     How many rows? How many pages (Heap Blocks)? Faster or slower than u1000?
--
-- T2. Estimate vs actual. Run:
--       EXPLAIN ANALYZE
--       SELECT count(*) FROM transactions
--       WHERE status = 'FAILED' AND channel = 'WEB';
--     Compare rows= (estimate) with actual rows=. Off by how much?
--
-- T3. Which plan node handles the most rows in Step 6? Which handles the fewest?
--
-- T4. Run EXPLAIN (no ANALYZE) for:
--       SELECT * FROM merchants WHERE merchant_account = 'merchant7';
--     Which index does it use, and why does that index already exist?
