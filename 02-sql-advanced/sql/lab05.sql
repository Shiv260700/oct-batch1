-- =====================================================================
-- Lab 05 — Capstone: The Slow Dashboard
-- The operations dashboard has 4 panels. Each panel runs one query.
-- The queries were written in a hurry. Make them fast AND correct.
--
-- Guide: labs/lab-05-capstone.md
-- Run Part A once, in order, BEFORE you change anything.
-- =====================================================================

-- ---------------------------------------------------------------------
-- PART A — Clean start + safety net
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Any query running longer than 60 seconds is cancelled.
-- A cancelled query is a finding: write it on your scorecard.
SET statement_timeout = '60s';
\timing on

-- ---------------------------------------------------------------------
-- PART B — The 4 dashboard queries (baselines)
-- For each one: run it, read the answer, then run the EXPLAIN version.
-- ---------------------------------------------------------------------

-- ===== Q1 · Daily summary panel ======================================
-- "Payments, amount and failures per channel on 15 March 2026"
SELECT channel,
       count(*)                                  AS payments,
       sum(amount)                               AS total_amount,
       count(*) FILTER (WHERE status = 'FAILED') AS failed
FROM transactions
WHERE txn_ts::date = DATE '2026-03-15'
GROUP BY channel
ORDER BY channel;

EXPLAIN (ANALYZE, BUFFERS)
SELECT channel,
       count(*)                                  AS payments,
       sum(amount)                               AS total_amount,
       count(*) FILTER (WHERE status = 'FAILED') AS failed
FROM transactions
WHERE txn_ts::date = DATE '2026-03-15'
GROUP BY channel
ORDER BY channel;

-- ===== Q2 · "Grocery merchants to call" panel ========================
-- "The 10 GROCERY merchants with the LOWEST successful revenue
--  (0 if they have none), so the sales team can call them"
-- (slow: around 10 seconds)
SELECT m.merchant_account,
       m.merchant_name,
       (SELECT coalesce(sum(t.amount), 0)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account
          AND t.status = 'SUCCESS') AS revenue
FROM merchants m
WHERE m.category = 'GROCERY'
ORDER BY revenue, m.merchant_account
LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account,
       m.merchant_name,
       (SELECT coalesce(sum(t.amount), 0)
        FROM transactions t
        WHERE t.payee_account = m.merchant_account
          AND t.status = 'SUCCESS') AS revenue
FROM merchants m
WHERE m.category = 'GROCERY'
ORDER BY revenue, m.merchant_account
LIMIT 10;

-- ===== Q3 · "Dormant merchants" panel ================================
-- "Merchants that have NEVER received a payment"
-- (slow: around 5 seconds)
SELECT m.merchant_account, m.merchant_name, m.city
FROM merchants m
WHERE m.merchant_account NOT IN (SELECT payee_account FROM transactions)
ORDER BY m.merchant_account;

EXPLAIN (ANALYZE, BUFFERS)
SELECT m.merchant_account, m.merchant_name, m.city
FROM merchants m
WHERE m.merchant_account NOT IN (SELECT payee_account FROM transactions)
ORDER BY m.merchant_account;

-- ===== Q4 · Customer history panel ===================================
-- "Customer u42@bank, page 251 of their history (20 per page, newest first)"
SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u42@bank'
ORDER BY t.txn_ts DESC, t.txn_id DESC
OFFSET 5000 LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS)
SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u42@bank'
ORDER BY t.txn_ts DESC, t.txn_id DESC
OFFSET 5000 LIMIT 20;

-- ---------------------------------------------------------------------
-- PART C — Save today's answers (so you can prove "same answer" later)
-- Takes about 20 seconds (Q2 and Q3 are slow).
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS lab05_q1_old, lab05_q2_old, lab05_q3_old, lab05_q4_old;

CREATE TABLE lab05_q1_old AS
SELECT channel, count(*) AS payments, sum(amount) AS total_amount,
       count(*) FILTER (WHERE status = 'FAILED') AS failed
FROM transactions
WHERE txn_ts::date = DATE '2026-03-15'
GROUP BY channel;

CREATE TABLE lab05_q2_old AS
SELECT m.merchant_account, m.merchant_name,
       (SELECT coalesce(sum(t.amount), 0) FROM transactions t
        WHERE t.payee_account = m.merchant_account AND t.status = 'SUCCESS') AS revenue
FROM merchants m
WHERE m.category = 'GROCERY'
ORDER BY revenue, m.merchant_account
LIMIT 10;

CREATE TABLE lab05_q3_old AS
SELECT m.merchant_account, m.merchant_name, m.city
FROM merchants m
WHERE m.merchant_account NOT IN (SELECT payee_account FROM transactions);

CREATE TABLE lab05_q4_old AS
SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t
JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u42@bank'
ORDER BY t.txn_ts DESC, t.txn_id DESC
OFFSET 5000 LIMIT 20;

SELECT 'q1' AS saved, count(*) AS rows FROM lab05_q1_old
UNION ALL SELECT 'q2', count(*) FROM lab05_q2_old
UNION ALL SELECT 'q3', count(*) FROM lab05_q3_old
UNION ALL SELECT 'q4', count(*) FROM lab05_q4_old;

-- =====================================================================
-- SCORECARD HELPERS (use these any time)
-- =====================================================================

-- H1. Which indexes have we created, and how big are they?
SELECT indexrelname                                   AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid))   AS size
FROM pg_stat_user_indexes
WHERE relname = 'transactions'
ORDER BY indexrelname;

-- H2. "Same answer?" check, shown here for Q1.
--     Replace the SELECT inside the brackets with YOUR new query.
--     Keep the same columns in the same order.
--     Both numbers must be 0.
SELECT
  (SELECT count(*) FROM (
      ( SELECT channel, count(*), sum(amount),
               count(*) FILTER (WHERE status = 'FAILED')
        FROM transactions
        WHERE txn_ts::date = DATE '2026-03-15'          -- <- your new query here
        GROUP BY channel )
      EXCEPT ALL
      TABLE lab05_q1_old) x)                       AS only_in_new,
  (SELECT count(*) FROM (
      TABLE lab05_q1_old
      EXCEPT ALL
      ( SELECT channel, count(*), sum(amount),
               count(*) FILTER (WHERE status = 'FAILED')
        FROM transactions
        WHERE txn_ts::date = DATE '2026-03-15'          -- <- your new query here
        GROUP BY channel )) x)                     AS only_in_old;

-- H3. Undo all your indexes and start a query again from scratch:
--     \i sql/reset.sql
--     SET statement_timeout = '60s';
--     (your lab05_qN_old tables are kept)

-- =====================================================================
-- Cleanup when the lab is over:
--   DROP TABLE IF EXISTS lab05_q1_old, lab05_q2_old, lab05_q3_old, lab05_q4_old;
-- =====================================================================
