-- =====================================================================
-- SQL Performance Workshop — shared dataset for ALL labs (01 to 06)
-- =====================================================================
-- Run once, connected to the paylab database:
--     cd sql-advanced
--     psql -h localhost -U labuser -d paylab
--     \i sql/00_setup.sql
--
-- Builds three tables of synthetic UPI-style payment data:
--     accounts      10,000 customers who pay        (u1@bank ... u10000@bank)
--      merchants      2,000 shops who get paid      (merchant1 ... merchant2000)
--     transactions 1,000,000 payments over 90 days  (1 Jan 2026 to 31 Mar 2026)
--
-- The data is random but REPEATABLE: setseed() makes every laptop build
-- exactly the same rows (PostgreSQL 15 or newer), so everyone's
-- answers match the trainer's.
--
-- Built-in "teaching features" (used in later labs):
--   * Rows are inserted in time order  -> txn_id and txn_ts rise together (BRIN demo)
--   * 3 very busy payers: u42, u43, u44 -> skewed data, "same query, different plan"
--   * Small merchants (low numbers) get far more payments than big numbers -> skew
--   * WEB payments fail much more often than APP payments -> correlated columns
--   * Accounts u9901..u10000 never pay      -> NOT EXISTS has real answers
--   * Merchants merchant1951..2000 never get paid
--   * Some PENDING payments have no payee yet (NULL) -> the NOT IN trap
--   * Foreign keys exist, but their columns are NOT indexed (PostgreSQL never
--     creates those indexes automatically)
--
-- Low on memory or disk? Change txn_rows below to 300000. Your numbers will
-- then differ from the trainer's slides.
-- =====================================================================

\set ON_ERROR_STOP on
\set txn_rows 1000000
\timing on

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS merchants;

-- Same seed -> same random numbers -> same data everywhere.
SELECT setseed(0.42);

-- ---------------------------------------------------------------------
-- 1. accounts: the customers who pay
-- ---------------------------------------------------------------------
CREATE TABLE accounts (
    account_id   TEXT PRIMARY KEY,           -- 'u1@bank'
    holder_name  TEXT NOT NULL,              -- 'Ravi Kumar'
    segment      TEXT NOT NULL,              -- REGULAR / PREMIUM / CORPORATE
    city         TEXT NOT NULL,
    opened_on    DATE NOT NULL
);

INSERT INTO accounts (account_id, holder_name, segment, city, opened_on)
SELECT 'u' || id || '@bank',
       (ARRAY['Ravi','Priya','Arjun','Ananya','Vikram','Sneha','Rahul','Divya',
              'Karthik','Meera','Suresh','Lakshmi','Amit','Pooja','Naveen',
              'Kavya','Rohan','Isha','Manoj','Deepa'])[1 + floor(r1 * 20)::int]
       || ' ' ||
       (ARRAY['Kumar','Sharma','Reddy','Iyer','Patel','Nair','Singh','Rao',
              'Gupta','Menon','Das','Joshi','Pillai','Verma','Shetty'])[1 + floor(r2 * 15)::int],
       CASE WHEN id IN (42, 43, 44) THEN 'CORPORATE'
            WHEN r3 < 0.80          THEN 'REGULAR'
            WHEN r3 < 0.95          THEN 'PREMIUM'
            ELSE                         'CORPORATE' END,
       (ARRAY['Mumbai','Bengaluru','Delhi','Chennai','Hyderabad','Pune',
              'Kolkata','Ahmedabad'])[1 + floor(r4 * 8)::int],
       DATE '2018-01-01' + floor(r5 * 2900)::int
FROM (
    SELECT id, random() AS r1, random() AS r2, random() AS r3,
               random() AS r4, random() AS r5
    FROM generate_series(1, 10000) AS id
) s;

-- ---------------------------------------------------------------------
-- 2. merchants: the shops who get paid
-- ---------------------------------------------------------------------
CREATE TABLE merchants (
    merchant_account TEXT PRIMARY KEY,       -- 'merchant1'
    merchant_name    TEXT NOT NULL,          -- 'Prime Grocery #1'
    category         TEXT NOT NULL,          -- 6 categories
    city             TEXT NOT NULL
);

INSERT INTO merchants (merchant_account, merchant_name, category, city)
SELECT 'merchant' || id,
       (ARRAY['Prime','City','Fresh','Quick','Royal','Metro','Sun','Star'])[1 + floor(r1 * 8)::int]
       || ' ' || initcap(cat) || ' #' || id,
       cat,
       (ARRAY['Mumbai','Bengaluru','Delhi','Chennai','Hyderabad','Pune',
              'Kolkata','Ahmedabad'])[1 + floor(r3 * 8)::int]
FROM (
    SELECT id, r1, r3,
           (ARRAY['GROCERY','FOOD','TRAVEL','FUEL','ELECTRONICS','UTILITIES'])[1 + floor(r2 * 6)::int] AS cat
    FROM (SELECT id, random() AS r1, random() AS r2, random() AS r3
          FROM generate_series(1, 2000) AS id) x
) s;

-- ---------------------------------------------------------------------
-- 3. transactions: 1 million payments
-- ---------------------------------------------------------------------
CREATE TABLE transactions (
    txn_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    upi_ref        TEXT          NOT NULL,   -- 12-character reference shown to the customer
    payer_account  TEXT          NOT NULL,   -- who paid      -> accounts.account_id
    payee_account  TEXT,                     -- who got paid  -> merchants.merchant_account
                                             --   (NULL only for some PENDING payments)
    amount         NUMERIC(12,2) NOT NULL,
    status         TEXT          NOT NULL,   -- SUCCESS / FAILED / PENDING
    channel        TEXT          NOT NULL,   -- APP / UPI_QR / WEB
    txn_ts         TIMESTAMP     NOT NULL
);

INSERT INTO transactions
       (upi_ref, payer_account, payee_account, amount, status, channel, txn_ts)
SELECT upi_ref, payer_account,
       CASE WHEN status = 'PENDING' AND r_null < 0.20 THEN NULL
            ELSE payee_account END,
       amount, status, channel, txn_ts
FROM (
    SELECT g, r_null,
           upper(left(md5(g::text), 12))                                   AS upi_ref,
           -- 3% of payments come from three busy corporate payers
           CASE WHEN r_heavy < 0.03
                THEN 'u' || (42 + floor(r_payer * 3)::int) || '@bank'
                ELSE 'u' || (1 + floor(r_payer * 9900)::int) || '@bank' END AS payer_account,
           -- squaring the random number favours small merchant numbers (skew)
           'merchant' || (1 + floor(1950 * r_payee * r_payee)::int)       AS payee_account,
           -- most payments are small, a few are large (Rs 1 to about Rs 49,000)
           round(greatest(1, exp(r_amt * 10.8))::numeric, 2)               AS amount,
           channel,
           -- WEB fails 15% of the time, APP 3%, UPI_QR 3.4%; 1% stay PENDING
           CASE WHEN r_status < fail_rate        THEN 'FAILED'
                WHEN r_status < fail_rate + 0.01 THEN 'PENDING'
                ELSE                                  'SUCCESS' END         AS status,
           date_trunc('second', TIMESTAMP '2026-01-01' + r_ts * INTERVAL '90 days') AS txn_ts
    FROM (
        SELECT g, r_heavy, r_payer, r_payee, r_amt, r_status, r_ts, r_null, channel,
               CASE channel WHEN 'WEB' THEN 0.15 WHEN 'APP' THEN 0.03 ELSE 0.034 END AS fail_rate
        FROM (
            SELECT g,
                   random() AS r_heavy, random() AS r_payer, random() AS r_payee,
                   random() AS r_amt,   random() AS r_chan,  random() AS r_status,
                   random() AS r_ts,    random() AS r_null
            FROM generate_series(1, :txn_rows) AS g
        ) r
        CROSS JOIN LATERAL (
            SELECT CASE WHEN r.r_chan < 0.60 THEN 'APP'
                        WHEN r.r_chan < 0.85 THEN 'UPI_QR'
                        ELSE                      'WEB' END AS channel
        ) c
    ) x
) y
ORDER BY txn_ts, g;          -- time order, like a real append-only payments table

-- Foreign keys, added after loading (faster). Note: NO index is created on
-- payer_account or payee_account. That is deliberate and is part of Lab 03.
ALTER TABLE transactions
    ADD CONSTRAINT transactions_payer_fk FOREIGN KEY (payer_account) REFERENCES accounts (account_id),
    ADD CONSTRAINT transactions_payee_fk FOREIGN KEY (payee_account) REFERENCES merchants (merchant_account);

-- Refresh planner statistics and the visibility map (needed for index-only scans).
VACUUM (ANALYZE) accounts;
VACUUM (ANALYZE) merchants;
VACUUM (ANALYZE) transactions;

\timing off

-- ---------------------------------------------------------------------
-- 4. Checkpoint: compare with the expected values
-- ---------------------------------------------------------------------
\echo
\echo '=== Checkpoint 1: row counts ==='
SELECT (SELECT count(*) FROM accounts)     AS accounts,
       (SELECT count(*) FROM merchants)    AS merchants,
       (SELECT count(*) FROM transactions) AS transactions;

\echo '=== Checkpoint 2: date range (should be 1 Jan to 31 Mar 2026) ==='
SELECT min(txn_ts) AS first_payment, max(txn_ts) AS last_payment
FROM transactions;

\echo '=== Checkpoint 3: status mix ==='
SELECT status, count(*) AS payments,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
FROM transactions GROUP BY status ORDER BY payments DESC;

\echo '=== Checkpoint 4: failure rate by channel ==='
SELECT channel, count(*) AS payments,
       round(100.0 * avg((status = 'FAILED')::int), 1) AS failed_pct
FROM transactions GROUP BY channel ORDER BY payments DESC;

\echo '=== Checkpoint 5: indexes (only the 3 primary keys) ==='
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('accounts', 'merchants', 'transactions')
ORDER BY tablename;
