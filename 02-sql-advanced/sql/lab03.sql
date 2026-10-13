-- =====================================================================
-- Lab 03 — Joins
-- Story: support now wants u1000@bank's payments WITH merchant names,
--        and managers want reports that combine accounts, payments and merchants.
--
-- Run one step at a time: copy a step into psql, or run the whole file:
--     \i sql/lab03.sql
-- Guide: labs/lab-03-joins.md
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — Clean start
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Keep plans simple: no parallel workers in this lab.
SET max_parallel_workers_per_gather = 0;

-- ---------------------------------------------------------------------
-- STEP 1 — Nested Loop: u1000's payments with merchant names
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT t.txn_id, t.amount, m.merchant_name
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u1000@bank';

-- 103 payments, but the join returns 102. Why?
SELECT count(*)                AS payments,
       count(t.payee_account)  AS with_payee
FROM transactions t
WHERE t.payer_account = 'u1000@bank';

-- ---------------------------------------------------------------------
-- STEP 2 — Hash Join: total spend per merchant category (all payments)
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;

-- ---------------------------------------------------------------------
-- STEP 3 — Merge Join: force it, only to see it (never do this in real code)
-- ---------------------------------------------------------------------
BEGIN;
SET LOCAL enable_hashjoin = off;
SET LOCAL enable_nestloop = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
GROUP BY m.category
ORDER BY total DESC;

ROLLBACK;   -- settings go back to normal

-- ---------------------------------------------------------------------
-- STEP 4 — Foreign keys are NOT indexed automatically
-- Question: top 5 CORPORATE customers in Hyderabad by amount paid
-- ---------------------------------------------------------------------
\d transactions

EXPLAIN (ANALYZE, BUFFERS)
SELECT a.account_id, a.holder_name, count(*) AS payments, sum(t.amount) AS total
FROM accounts a
JOIN transactions t ON t.payer_account = a.account_id
WHERE a.segment = 'CORPORATE' AND a.city = 'Hyderabad'
GROUP BY a.account_id, a.holder_name
ORDER BY total DESC
LIMIT 5;

-- Index the foreign key column, then run the same query again
CREATE INDEX idx_txn_payer ON transactions (payer_account);

EXPLAIN (ANALYZE, BUFFERS)
SELECT a.account_id, a.holder_name, count(*) AS payments, sum(t.amount) AS total
FROM accounts a
JOIN transactions t ON t.payer_account = a.account_id
WHERE a.segment = 'CORPORATE' AND a.city = 'Hyderabad'
GROUP BY a.account_id, a.holder_name
ORDER BY total DESC
LIMIT 5;

-- ---------------------------------------------------------------------
-- STEP 5 — Three tables: join order and filter pushdown
-- Question: PREMIUM customers paying Mumbai merchants, by category
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN accounts  a ON a.account_id       = t.payer_account
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE a.segment = 'PREMIUM'
  AND m.city    = 'Mumbai'
GROUP BY m.category
ORDER BY total DESC;

-- Same question, tables written in a different order: compare the plan
EXPLAIN
SELECT m.category, count(*) AS payments, sum(t.amount) AS total
FROM merchants m
JOIN transactions t ON t.payee_account = m.merchant_account
JOIN accounts  a    ON a.account_id    = t.payer_account
WHERE a.segment = 'PREMIUM'
  AND m.city    = 'Mumbai'
GROUP BY m.category
ORDER BY total DESC;

-- ---------------------------------------------------------------------
-- STEP 6 — The LEFT JOIN trap: condition in ON vs in WHERE
-- Question: FAILED payments per merchant on 31 March, list ALL merchants
-- ---------------------------------------------------------------------
-- A: condition in ON
SELECT count(*) AS merchants_listed
FROM (
    SELECT m.merchant_account, count(t.txn_id) AS failed
    FROM merchants m
    LEFT JOIN transactions t
           ON t.payee_account = m.merchant_account
          AND t.status = 'FAILED'
          AND t.txn_ts >= '2026-03-31'
    GROUP BY m.merchant_account
) x;

-- B: condition in WHERE
SELECT count(*) AS merchants_listed
FROM (
    SELECT m.merchant_account, count(t.txn_id) AS failed
    FROM merchants m
    LEFT JOIN transactions t
           ON t.payee_account = m.merchant_account
    WHERE t.status = 'FAILED'
      AND t.txn_ts >= '2026-03-31'
    GROUP BY m.merchant_account
) x;

-- ---------------------------------------------------------------------
-- STEP 7 — EXISTS vs JOIN + DISTINCT
-- Question: which Pune merchants have received at least one payment?
-- ---------------------------------------------------------------------
-- The other foreign key column needs an index too
CREATE INDEX idx_txn_payee ON transactions (payee_account);

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

-- ---------------------------------------------------------------------
-- STEP 8 — NOT EXISTS vs NOT IN (the NULL trap)
-- Question: which merchants have NEVER been paid?
-- ---------------------------------------------------------------------
-- A: NOT EXISTS
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.merchant_name
FROM merchants m
WHERE NOT EXISTS (SELECT 1 FROM transactions t
                  WHERE t.payee_account = m.merchant_account);

-- B: the NULL trap in one line
SELECT 'merchant1' NOT IN ('merchant2', NULL) AS is_it_true;

-- C: proof on real data (small version, runs fast)
--    "merchants with no PENDING payment" (some PENDING payments have NULL payee)
SELECT count(*) AS with_not_exists
FROM merchants m
WHERE NOT EXISTS (SELECT 1 FROM transactions t
                  WHERE t.payee_account = m.merchant_account
                    AND t.status = 'PENDING');

SELECT count(*) AS with_not_in
FROM merchants m
WHERE m.merchant_account NOT IN (SELECT t.payee_account FROM transactions t
                                 WHERE t.status = 'PENDING');

-- D: plan only. Do NOT add ANALYZE: it runs for over a minute and returns 0 rows
EXPLAIN
SELECT m.merchant_account, m.merchant_name
FROM merchants m
WHERE m.merchant_account NOT IN (SELECT t.payee_account FROM transactions t);

-- ---------------------------------------------------------------------
-- STEP 9 — Memory: when the hash table does not fit in work_mem
-- Question: payments per customer segment
-- ---------------------------------------------------------------------
SHOW work_mem;

EXPLAIN (ANALYZE, BUFFERS)
SELECT a.segment, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN accounts a ON a.account_id = t.payer_account
GROUP BY a.segment;

BEGIN;
SET LOCAL work_mem = '64kB';      -- tiny memory, only for this transaction

EXPLAIN (ANALYZE, BUFFERS)
SELECT a.segment, count(*) AS payments, sum(t.amount) AS total
FROM transactions t
JOIN accounts a ON a.account_id = t.payer_account
GROUP BY a.segment;

ROLLBACK;

-- =====================================================================
-- TRY IT YOURSELF (answers in trainer/lab-03-answers.md)
-- =====================================================================
-- T1. Re-run the Step 1 query now (idx_txn_payer exists).
--     Which join does PostgreSQL choose now? Why did it change?
--
-- T2. Which ACCOUNTS have never made a payment? Write it with NOT EXISTS.
--     How many rows? Which join node appears?
--
-- T3. Using the correct report from Step 6 (version A), how many merchants
--     had ZERO failed payments on 31 March? Does 2000 - 439 agree?
--
-- T4. Add  WHERE t.payee_account IS NOT NULL  inside the NOT IN subquery of
--     Step 8D. Run EXPLAIN (not ANALYZE) first.
--     Is the answer correct now? Is the plan cheap now? What is the better fix?
