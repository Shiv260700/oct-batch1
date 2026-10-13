-- =====================================================================
-- Lab 04 — Rewriting Queries for Performance
-- Story: the operations team's merchant dashboard is slow.
--        Same answers, less work: rewrite the SQL, then PROVE the
--        answer did not change.
--
-- Run one step at a time: copy a step into psql, or run the whole file:
--     \i sql/lab04.sql
-- Guide: labs/lab-04-rewriting.md
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — Clean start
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Keep plans short and readable:
SET max_parallel_workers_per_gather = 0;   -- no parallel workers (covered in Lab 01)
SET jit = off;                             -- no JIT compiler notes in big plans

-- ---------------------------------------------------------------------
-- STEP 1 — Correlated subquery: one count per merchant
-- Question: how many payments did each merchant receive?
-- (First 20 merchants only: the full list would take over a minute.)
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       (SELECT count(*)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m
ORDER BY m.merchant_account
LIMIT 20;

-- The full list: plan only (do NOT add ANALYZE: it runs ~2000 full scans)
EXPLAIN
SELECT m.merchant_account,
       (SELECT count(*)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m;

-- ---------------------------------------------------------------------
-- STEP 2 — Rewrite: group once, then join
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       COALESCE(c.payments, 0) AS payments
FROM merchants m
LEFT JOIN (SELECT payee_account, count(*) AS payments
           FROM transactions
           GROUP BY payee_account) c
       ON c.payee_account = m.merchant_account;

-- ---------------------------------------------------------------------
-- STEP 3 — Or: give the subquery an index
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_payee ON transactions (payee_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       (SELECT count(*)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account) AS payments
FROM merchants m;

-- ---------------------------------------------------------------------
-- STEP 4 — PROVE the rewrite gives the same answer
-- Template: (A EXCEPT ALL B) and (B EXCEPT ALL A) must both be 0 rows.
-- ---------------------------------------------------------------------
WITH a AS (     -- original: correlated subquery
    SELECT m.merchant_account,
           (SELECT count(*) FROM transactions t
            WHERE t.payee_account = m.merchant_account) AS payments
    FROM merchants m
), b AS (       -- rewrite: group once, LEFT JOIN
    SELECT m.merchant_account, COALESCE(c.payments, 0) AS payments
    FROM merchants m
    LEFT JOIN (SELECT payee_account, count(*) AS payments
               FROM transactions GROUP BY payee_account) c
           ON c.payee_account = m.merchant_account
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_original,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_rewrite;

-- A "faster" rewrite with a bug: INNER JOIN instead of LEFT JOIN
WITH a AS (
    SELECT m.merchant_account,
           (SELECT count(*) FROM transactions t
            WHERE t.payee_account = m.merchant_account) AS payments
    FROM merchants m
), b AS (
    SELECT m.merchant_account, c.payments
    FROM merchants m
    JOIN (SELECT payee_account, count(*) AS payments
          FROM transactions GROUP BY payee_account) c
      ON c.payee_account = m.merchant_account
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_original,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_rewrite;

-- ---------------------------------------------------------------------
-- STEP 5 — Pre-aggregate before the join: sales per category
-- ---------------------------------------------------------------------
-- 5a. Join first, then group (joins 1,000,000 rows)
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;

-- 5b. Group by merchant first, then join (joins ~1,950 rows)
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, sum(s.payments) AS payments, sum(s.total) AS total
FROM (SELECT payee_account, count(*) AS payments, sum(amount) AS total
      FROM transactions
      GROUP BY payee_account) s
JOIN merchants m ON m.merchant_account = s.payee_account
GROUP BY m.category
ORDER BY total DESC;

-- 5c. Prove: same totals
WITH a AS (
    SELECT m.category, count(*) AS payments, sum(t.amount) AS total
    FROM transactions t
    JOIN merchants m ON m.merchant_account = t.payee_account
    GROUP BY m.category
), b AS (
    SELECT m.category, sum(s.payments) AS payments, sum(s.total) AS total
    FROM (SELECT payee_account, count(*) AS payments, sum(amount) AS total
          FROM transactions GROUP BY payee_account) s
    JOIN merchants m ON m.merchant_account = s.payee_account
    GROUP BY m.category
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_original,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_rewrite;

-- ---------------------------------------------------------------------
-- STEP 6 — CTEs (WITH): inlined or materialized?
-- Question: sales of ONE merchant, using a "merchant_sales" CTE
-- ---------------------------------------------------------------------
-- 6a. Default: used once -> PostgreSQL merges it into the main query
EXPLAIN (ANALYZE, BUFFERS)
WITH merchant_sales AS (
    SELECT payee_account, count(*) AS payments, sum(amount) AS total
    FROM transactions
    GROUP BY payee_account
)
SELECT * FROM merchant_sales
WHERE payee_account = 'merchant7';

-- 6b. MATERIALIZED: compute the whole CTE first, filter afterwards
EXPLAIN (ANALYZE, BUFFERS)
WITH merchant_sales AS MATERIALIZED (
    SELECT payee_account, count(*) AS payments, sum(amount) AS total
    FROM transactions
    GROUP BY payee_account
)
SELECT * FROM merchant_sales
WHERE payee_account = 'merchant7';

-- 6c. Used twice -> computed once by default; NOT MATERIALIZED forces merging
EXPLAIN
WITH merchant_sales AS (
    SELECT payee_account, count(*) AS payments, sum(amount) AS total
    FROM transactions GROUP BY payee_account
)
SELECT a.payee_account, a.total, b.total
FROM merchant_sales a JOIN merchant_sales b ON b.payee_account = 'merchant1'
WHERE a.payee_account = 'merchant7';

EXPLAIN
WITH merchant_sales AS NOT MATERIALIZED (
    SELECT payee_account, count(*) AS payments, sum(amount) AS total
    FROM transactions GROUP BY payee_account
)
SELECT a.payee_account, a.total, b.total
FROM merchant_sales a JOIN merchant_sales b ON b.payee_account = 'merchant1'
WHERE a.payee_account = 'merchant7';

-- ---------------------------------------------------------------------
-- STEP 7 — Top-N per group
-- ---------------------------------------------------------------------
-- 7a. Latest payment of every payer: row_number()
EXPLAIN (ANALYZE, BUFFERS)
SELECT payer_account, txn_id, txn_ts, amount
FROM (SELECT payer_account, txn_id, txn_ts, amount,
             row_number() OVER (PARTITION BY payer_account
                                ORDER BY txn_ts DESC, txn_id DESC) AS rn
      FROM transactions) ranked
WHERE rn = 1;

-- 7b. Same question: DISTINCT ON (PostgreSQL only)
EXPLAIN (ANALYZE, BUFFERS)
SELECT DISTINCT ON (payer_account)
       payer_account, txn_id, txn_ts, amount
FROM transactions
ORDER BY payer_account, txn_ts DESC, txn_id DESC;

-- 7c. Prove: same rows
WITH a AS (
    SELECT payer_account, txn_id, txn_ts, amount
    FROM (SELECT payer_account, txn_id, txn_ts, amount,
                 row_number() OVER (PARTITION BY payer_account
                                    ORDER BY txn_ts DESC, txn_id DESC) AS rn
          FROM transactions) ranked
    WHERE rn = 1
), b AS (
    SELECT DISTINCT ON (payer_account) payer_account, txn_id, txn_ts, amount
    FROM transactions
    ORDER BY payer_account, txn_ts DESC, txn_id DESC
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_a,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_b;

-- 7d. Latest 3 payments of every merchant: LATERAL + index
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

-- ---------------------------------------------------------------------
-- STEP 8 — Pagination for the busy payer u42@bank (~10,000 payments)
-- ---------------------------------------------------------------------
CREATE INDEX idx_txn_payer_ts_id ON transactions (payer_account, txn_ts DESC, txn_id DESC);

-- 8a. OFFSET: page 451 (rows 9,001 - 9,020)
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC, txn_id DESC
OFFSET 9000 LIMIT 20;

-- 8b. Keyset: remember the LAST row of the previous page (row 9,000) ...
SELECT txn_ts AS last_ts, txn_id AS last_id
FROM transactions
WHERE payer_account = 'u42@bank'
ORDER BY txn_ts DESC, txn_id DESC
OFFSET 8999 LIMIT 1 \gset

\echo 'Cursor (last row of previous page):' :'last_ts' :last_id

-- ... and continue right after it
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, txn_ts, amount
FROM transactions
WHERE payer_account = 'u42@bank'
  AND (txn_ts, txn_id) < (:'last_ts', :last_id)
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 20;

-- 8c. Prove: same 20 rows
WITH a AS (
    SELECT txn_id, txn_ts, amount FROM transactions
    WHERE payer_account = 'u42@bank'
    ORDER BY txn_ts DESC, txn_id DESC
    OFFSET 9000 LIMIT 20
), b AS (
    SELECT txn_id, txn_ts, amount FROM transactions
    WHERE payer_account = 'u42@bank'
      AND (txn_ts, txn_id) < (:'last_ts', :last_id)
    ORDER BY txn_ts DESC, txn_id DESC
    LIMIT 20
)
SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x) AS only_in_offset,
       (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) x) AS only_in_keyset;

-- ---------------------------------------------------------------------
-- STEP 9 — Statistics: when the planner's guess is wrong
-- ---------------------------------------------------------------------
-- 9a. What the planner knows about each column
SELECT attname, most_common_vals, most_common_freqs
FROM pg_stats
WHERE tablename = 'transactions'
  AND attname IN ('status', 'channel');

-- 9b. The guess for FAILED + WEB
EXPLAIN ANALYZE
SELECT count(*) FROM transactions
WHERE status = 'FAILED' AND channel = 'WEB';

-- 9c. Teach the planner that the two columns are related
CREATE STATISTICS st_status_channel (mcv) ON status, channel FROM transactions;
ANALYZE transactions;

EXPLAIN ANALYZE
SELECT count(*) FROM transactions
WHERE status = 'FAILED' AND channel = 'WEB';

-- =====================================================================
-- TRY IT YOURSELF (answers in trainer/lab-04-answers.md)
-- =====================================================================
-- T1. Rewrite this correlated subquery as "group once, then join".
--     Prove it with the EXCEPT ALL template.
--       SELECT a.account_id,
--              (SELECT max(t.amount) FROM transactions t
--               WHERE t.payer_account = a.account_id) AS biggest_payment
--       FROM accounts a;
--     Careful: 100 accounts never paid. What must biggest_payment be for them?
--
-- T2. Latest 2 payments of every payer: change Step 7a to return 2 rows
--     per payer. Why can't DISTINCT ON do this?
--
-- T3. Run Step 6b's MATERIALIZED CTE for 'merchant1' and for 'merchant1500'.
--     Is the time different? Why not?
--
-- T4. Keyset: fetch the NEXT page after the one in Step 8b.
--     (Hint: \gset the last row of that page.)
