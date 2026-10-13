-- =====================================================================
-- Lab 06 — Functions and Procedures
-- Story: the "show my payments" query for u1000@bank becomes a
-- reusable function, like a Python function: def get_payments(payer, limit=5)
--
-- Run one step at a time: copy a step into psql, or run the whole file:
--     \i sql/lab06.sql
-- Guide: labs/lab-06-functions.md
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — Clean start
-- ---------------------------------------------------------------------
\i sql/reset.sql

-- Some steps below show errors on purpose: keep going after an error.
\set ON_ERROR_STOP off

-- The story query needs the payer index from Lab 01.
CREATE INDEX idx_txn_payer ON transactions (payer_account);

-- ---------------------------------------------------------------------
-- STEP 1 — The story query, written by hand every time
-- ---------------------------------------------------------------------
SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t
LEFT JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u1000@bank'
ORDER BY t.txn_ts DESC
LIMIT 5;

-- ---------------------------------------------------------------------
-- STEP 2 — Wrap it in a SQL function (like Python "def")
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS get_payments(text, int);

CREATE FUNCTION get_payments(p_payer text, p_limit int DEFAULT 5)
RETURNS TABLE (txn_id bigint, txn_ts timestamp, amount numeric,
               status text, merchant_name text)
LANGUAGE sql
STABLE
AS $$
    SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
    FROM transactions t
    LEFT JOIN merchants m ON m.merchant_account = t.payee_account
    WHERE t.payer_account = p_payer
    ORDER BY t.txn_ts DESC
    LIMIT p_limit;
$$;

SELECT * FROM get_payments('u1000@bank');                          -- default: 5 rows
SELECT * FROM get_payments('u1000@bank', 2);                       -- positional
SELECT * FROM get_payments(p_limit => 3, p_payer => 'u42@bank');   -- named

-- ---------------------------------------------------------------------
-- STEP 3 — Look inside: can EXPLAIN see the function's query?
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_payments('u1000@bank');

-- ---------------------------------------------------------------------
-- STEP 4 — PL/pgSQL: variables, IF/ELSIF, NOTICE, errors
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION payment_summary(p_payer text)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total   int;
    v_failed  int;
    v_amount  numeric;
    v_level   text;
BEGIN
    -- 1. Validate the input
    PERFORM 1 FROM accounts WHERE account_id = p_payer;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown payer: %', p_payer
              USING HINT = 'Payer ids look like u1000@bank';
    END IF;

    -- 2. Store query results in variables
    SELECT count(*),
           count(*) FILTER (WHERE status = 'FAILED'),
           coalesce(sum(amount) FILTER (WHERE status = 'SUCCESS'), 0)
    INTO v_total, v_failed, v_amount
    FROM transactions
    WHERE payer_account = p_payer;

    -- 3. Decide with IF / ELSIF / ELSE
    IF v_total = 0 THEN
        v_level := 'NEW';
    ELSIF v_failed * 10 > v_total THEN
        v_level := 'CHECK';          -- more than 10% failed
    ELSE
        v_level := 'OK';
    END IF;

    RAISE NOTICE 'payer %: % payments, % failed', p_payer, v_total, v_failed;

    RETURN format('%s | payments=%s failed=%s paid=Rs %s | %s',
                  p_payer, v_total, v_failed, v_amount, v_level);
END;
$$;

SELECT payment_summary('u1000@bank');
SELECT payment_summary('u7501@bank');      -- 15 of 109 failed
SELECT payment_summary('u9950@bank');      -- one of the 100 accounts that never paid
SELECT payment_summary('nobody@bank');     -- ERROR: Unknown payer

-- ---------------------------------------------------------------------
-- STEP 5 — RETURN QUERY and catching errors (like try / except)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_payments_checked(p_payer text, p_limit int DEFAULT 5)
RETURNS TABLE (txn_id bigint, txn_ts timestamp, amount numeric,
               status text, merchant_name text)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_limit NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'p_limit must be 1..100, got %', p_limit;
    END IF;

    RETURN QUERY
        SELECT * FROM get_payments(p_payer, p_limit);

    IF NOT FOUND THEN
        RAISE NOTICE 'No payments for %', p_payer;
    END IF;
END;
$$;

SELECT * FROM get_payments_checked('u1000@bank', 3);
SELECT * FROM get_payments_checked('u9950@bank');          -- NOTICE, 0 rows
SELECT * FROM get_payments_checked('u1000@bank', 500);     -- ERROR

CREATE OR REPLACE FUNCTION safe_summary(p_payer text)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN payment_summary(p_payer);
EXCEPTION
    WHEN others THEN                      -- like Python: except Exception as e
        RETURN 'error: ' || SQLERRM;
END;
$$;

SELECT safe_summary('nobody@bank');       -- no ERROR, a text message instead

-- ---------------------------------------------------------------------
-- STEP 6 — Volatility: IMMUTABLE / STABLE / VOLATILE
-- ---------------------------------------------------------------------
SELECT DISTINCT proname, provolatile
FROM pg_proc
WHERE proname IN ('upper', 'now', 'random', 'get_payments', 'payment_summary')
ORDER BY proname;                          -- i = immutable, s = stable, v = volatile

-- An IMMUTABLE helper: same input -> same output, forever
CREATE OR REPLACE FUNCTION clean_name(p_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$ SELECT lower(trim(p_name)) $$;

SELECT clean_name('  RAVI Kumar ');        -- 'ravi kumar'

-- Support searches customers by name, typed any way
EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name
FROM accounts
WHERE clean_name(holder_name) = clean_name('  RAVI Kumar ');

-- IMMUTABLE functions can be used in an expression index
CREATE INDEX idx_acc_clean_name ON accounts (clean_name(holder_name));

EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name
FROM accounts
WHERE clean_name(holder_name) = clean_name('  RAVI Kumar ');

-- A STABLE function cannot be used in an index
CREATE OR REPLACE FUNCTION clean_name_stable(p_name text)
RETURNS text LANGUAGE plpgsql STABLE
AS $$ BEGIN RETURN lower(trim(p_name)); END; $$;

CREATE INDEX idx_acc_bad ON accounts (clean_name_stable(holder_name));   -- ERROR

-- ---------------------------------------------------------------------
-- STEP 7 — A function on the COLUMN hides the index
-- ---------------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)          -- function on the column: index not used
SELECT count(*) FROM transactions
WHERE clean_name(payer_account) = 'u1000@bank';

EXPLAIN (ANALYZE, BUFFERS)          -- function on the value: index used
SELECT count(*) FROM transactions
WHERE payer_account = clean_name('  U1000@BANK ');

-- ---------------------------------------------------------------------
-- STEP 8 — Row-by-row LOOP vs one set-based statement
-- Task: build a summary row (payments, amount paid) for every account.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS customer_totals;
CREATE TEMP TABLE customer_totals (account_id text, payments bigint, paid numeric);

\timing on

-- Version A: a loop, one query + one INSERT per account (10,000 times)
BEGIN;
DO $$
DECLARE
    r        record;
    v_count  bigint;
    v_paid   numeric;
BEGIN
    FOR r IN SELECT account_id FROM accounts LOOP
        SELECT count(*), coalesce(sum(amount), 0)
        INTO v_count, v_paid
        FROM transactions
        WHERE payer_account = r.account_id AND status = 'SUCCESS';

        INSERT INTO customer_totals VALUES (r.account_id, v_count, v_paid);
    END LOOP;
END;
$$;
ROLLBACK;

-- Version B: one statement does all 10,000 accounts
BEGIN;
INSERT INTO customer_totals
SELECT a.account_id, count(t.txn_id), coalesce(sum(t.amount), 0)
FROM accounts a
LEFT JOIN transactions t
       ON t.payer_account = a.account_id AND t.status = 'SUCCESS'
GROUP BY a.account_id;
ROLLBACK;

\timing off

-- ---------------------------------------------------------------------
-- STEP 9 — Plan caching: one plan for every value?
-- Functions and PREPAREd statements may reuse one "generic" plan.
-- ---------------------------------------------------------------------
SET max_parallel_workers_per_gather = 0;      -- keep plans simple
CREATE INDEX idx_txn_status ON transactions (status);

PREPARE by_status(text) AS
    SELECT count(*), sum(amount)
    FROM transactions
    WHERE status = $1;

-- Custom plan: built for the actual value
SET plan_cache_mode = force_custom_plan;
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('PENDING');    -- 1% of rows
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('SUCCESS');    -- 94% of rows

-- Generic plan: one plan, built without knowing the value
SET plan_cache_mode = force_generic_plan;
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('PENDING');
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('SUCCESS');

RESET plan_cache_mode;                -- default "auto": decides after 5 runs
RESET max_parallel_workers_per_gather;
DEALLOCATE by_status;

-- ---------------------------------------------------------------------
-- STEP 10 — Procedures: CALL, and COMMIT in batches
-- Works on a copy table, so the real data is not changed.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS pending_queue;
CREATE TABLE pending_queue AS
SELECT txn_id, status, txn_ts
FROM transactions
WHERE status = 'PENDING';

SELECT status, count(*) FROM pending_queue GROUP BY status;

CREATE OR REPLACE PROCEDURE expire_pending(p_before timestamp, p_batch int DEFAULT 2000)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows  int;
    v_batch int := 0;
BEGIN
    LOOP
        UPDATE pending_queue SET status = 'EXPIRED'
        WHERE txn_id IN (SELECT txn_id FROM pending_queue
                         WHERE status = 'PENDING' AND txn_ts < p_before
                         LIMIT p_batch);
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        EXIT WHEN v_rows = 0;

        v_batch := v_batch + 1;
        COMMIT;                                   -- save this batch now
        RAISE NOTICE 'batch %: % rows expired', v_batch, v_rows;
    END LOOP;
END;
$$;

CALL expire_pending('2026-03-01');

SELECT status, count(*) FROM pending_queue GROUP BY status ORDER BY status;

-- A function is not allowed to COMMIT
CREATE OR REPLACE FUNCTION try_commit() RETURNS void
LANGUAGE plpgsql AS $$ BEGIN COMMIT; END; $$;

SELECT try_commit();                              -- ERROR

-- ---------------------------------------------------------------------
-- STEP 11 — Good practice: name parameters with p_
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS count_payments(text);

CREATE FUNCTION count_payments(payer_account text)
RETURNS bigint
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN (SELECT count(*) FROM transactions
            WHERE payer_account = payer_account);   -- column or parameter?
END;
$$;

SELECT count_payments('u1000@bank');              -- ERROR: ambiguous

DROP FUNCTION count_payments(text);

CREATE FUNCTION count_payments(p_payer text)
RETURNS bigint
LANGUAGE sql STABLE STRICT
AS $$ SELECT count(*) FROM transactions WHERE payer_account = p_payer $$;

SELECT count_payments('u1000@bank');              -- 103
SELECT count_payments(NULL);                      -- STRICT: NULL in -> NULL out, query not run

-- =====================================================================
-- TRY IT YOURSELF (answers in trainer/lab-06-answers.md)
-- =====================================================================
-- T1. Write a SQL function merchant_payments(p_merchant text, p_limit int DEFAULT 10)
--     returning the latest payments received by a merchant. Call it for 'merchant7'.
--
-- T2. Extend payment_summary: add a level 'VIP' when total SUCCESS amount
--     is above Rs 5,000,000. Which payers reach it? (try u42@bank and u1000@bank)
--
-- T3. Which volatility would you give each function, and why?
--       a) gst(amount) returns amount * 0.18
--       b) payments_today(p_payer) counts payments where txn_ts >= current_date
--       c) new_upi_ref() returns a random 12-character reference
--
-- T4. Rewrite this as ONE set-based statement (no loop):
--       FOR r IN SELECT account_id FROM accounts WHERE segment = 'PREMIUM' LOOP
--           UPDATE accounts SET city = upper(city) WHERE account_id = r.account_id;
--       END LOOP;
--
-- T5. EXPLAIN (ANALYZE) SELECT * FROM get_payments_checked('u1000@bank');
--     Can you see the index scan? How would you check the inner plan instead?
