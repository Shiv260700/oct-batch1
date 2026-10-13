# Lab 06 — Functions and Procedures

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab06.sql`

## The story

- Support types the "show my payments" query for `u1000@bank` by hand, again and again.
- **Your job:** turn it into a **reusable function**, like a Python function, and keep it **fast**.

## You will be able to

- Write a SQL function with parameters, defaults and named arguments
- Write PL/pgSQL with variables, `IF`, `RAISE`, `RETURN QUERY` and error handling
- Choose the right volatility: `IMMUTABLE` / `STABLE` / `VOLATILE`
- Avoid the 3 classic function performance traps
- Write a procedure that commits in batches

## Python ↔ PostgreSQL

| Python | PostgreSQL |
|---|---|
| `def get_payments(payer, limit=5):` | `CREATE FUNCTION get_payments(p_payer text, p_limit int DEFAULT 5)` |
| `return rows` | `RETURNS TABLE (...)` + a `SELECT` |
| `get_payments(limit=3, payer="u42")` | `get_payments(p_limit => 3, p_payer => 'u42@bank')` |
| `raise ValueError("...")` | `RAISE EXCEPTION '...'` |
| `try: ... except Exception as e:` | `BEGIN ... EXCEPTION WHEN others THEN ... SQLERRM` |
| `print(...)` | `RAISE NOTICE '...'` |

> Your milliseconds will differ from the trainer's. **Rows, pages and plan shapes will match.**

---

## Step 0 — Clean start

▶️ **Run**

```sql
\i sql/reset.sql
\set ON_ERROR_STOP off
CREATE INDEX idx_txn_payer ON transactions (payer_account);
```

- Some steps show errors **on purpose**. `ON_ERROR_STOP off` lets the file keep going.
- The payer index from Lab 01 keeps the story query fast.

---

## Step 1 — The story query, by hand

❓ What does support type every time?

▶️ **Run**

```sql
SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t
LEFT JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u1000@bank'
ORDER BY t.txn_ts DESC
LIMIT 5;
```

👀 **See**

```text
 txn_id |       txn_ts        |  amount  | status  |    merchant_name
--------+---------------------+----------+---------+---------------------
 998042 | 2026-03-31 19:44:51 | 28471.72 | SUCCESS | Fresh Travel #1293
 991566 | 2026-03-31 05:47:20 | 12351.91 | SUCCESS | Quick Grocery #1817
 971246 | 2026-03-29 09:33:57 |   821.58 | SUCCESS | Metro Travel #751
 970648 | 2026-03-29 08:18:36 |  2513.28 | SUCCESS | Metro Grocery #1116
 953145 | 2026-03-27 18:40:16 |  1930.30 | SUCCESS | Fresh Food #421
```

- 7 lines of SQL, copied into every screen, and one typo away from a bug.

---

## Step 2 — A SQL function (Python `def`)

❓ How do we write it **once** and call it with any payer?

▶️ **Run**

```sql
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
```

👀 **See**

- Call 1: the **same 5 rows** as Step 1.
- Call 2: the top 2 rows only.
- Call 3: 3 rows for the busy payer `u42@bank`.

| Part | Meaning |
|---|---|
| `p_payer text` | Input parameter (the `p_` prefix is explained in Step 11) |
| `DEFAULT 5` | Optional parameter, like `limit=5` in Python |
| `RETURNS TABLE (...)` | The function returns rows, used like a table: `SELECT * FROM ...` |
| `LANGUAGE sql` | Body is plain SQL |
| `STABLE` | Promise: reads data, does not change it (Step 6) |
| `$$ ... $$` | Quotes around the body |

📌 **Remember:** a function = a named, reusable query with parameters.

---

## Step 3 — Can `EXPLAIN` see inside?

❓ Is the function still fast? Does it still use the index?

🤔 **Predict:** will the plan show the index, or just "a function"?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM get_payments('u1000@bank');
```

👀 **See** (trimmed)

```text
 Limit  (... actual time=0.397..0.398 rows=5 loops=1)
   ->  Sort  (... rows=5 loops=1)
         Sort Key: t.txn_ts DESC
         ->  Hash Left Join  (... rows=103 loops=1)
               ->  Bitmap Heap Scan on transactions t  (... rows=103 loops=1)
                     ->  Bitmap Index Scan on idx_txn_payer  (... rows=103 loops=1)
                           Index Cond: (payer_account = 'u1000@bank'::text)
               ->  Hash  (... rows=2000 loops=1)
                     ->  Seq Scan on merchants m  (... rows=2000 loops=1)
 Execution Time: 0.407 ms
```

- A simple `LANGUAGE sql` function is **inlined**: PostgreSQL pastes its body into your query.
- So you see the **real plan**, with `Index Cond`. Still 0.4 ms.
- A PL/pgSQL function shows only `Function Scan` (Try it T5).

📌 **Remember:** simple SQL functions cost nothing extra. Their plan is visible.

---

## Step 4 — PL/pgSQL: variables, IF, NOTICE, errors

❓ Support wants a one-line health summary per customer.

▶️ **Run** (full code in `sql/lab06.sql`)

```sql
CREATE OR REPLACE FUNCTION payment_summary(p_payer text)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total int;  v_failed int;  v_amount numeric;  v_level text;
BEGIN
    PERFORM 1 FROM accounts WHERE account_id = p_payer;      -- does the payer exist?
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown payer: %', p_payer
              USING HINT = 'Payer ids look like u1000@bank';
    END IF;

    SELECT count(*), count(*) FILTER (WHERE status = 'FAILED'),
           coalesce(sum(amount) FILTER (WHERE status = 'SUCCESS'), 0)
    INTO v_total, v_failed, v_amount
    FROM transactions WHERE payer_account = p_payer;

    IF v_total = 0 THEN            v_level := 'NEW';
    ELSIF v_failed * 10 > v_total THEN v_level := 'CHECK';   -- more than 10% failed
    ELSE                            v_level := 'OK';
    END IF;

    RAISE NOTICE 'payer %: % payments, % failed', p_payer, v_total, v_failed;
    RETURN format('%s | payments=%s failed=%s paid=Rs %s | %s',
                  p_payer, v_total, v_failed, v_amount, v_level);
END;
$$;

SELECT payment_summary('u1000@bank');
SELECT payment_summary('u7501@bank');
SELECT payment_summary('u9950@bank');
SELECT payment_summary('nobody@bank');
```

👀 **See**

```text
 u1000@bank | payments=103 failed=4 paid=Rs 724985.83 | OK
 u7501@bank | payments=109 failed=15 paid=Rs 270420.11 | CHECK
 u9950@bank | payments=0 failed=0 paid=Rs 0 | NEW
ERROR:  Unknown payer: nobody@bank
HINT:  Payer ids look like u1000@bank
```

| Part | Meaning |
|---|---|
| `DECLARE v_total int;` | Local variables (prefix `v_`) |
| `SELECT ... INTO v_total` | Store a query result in variables |
| `PERFORM` | Run a query, throw the result away |
| `FOUND` | `true` if the last query found a row |
| `RAISE NOTICE` | Print a message (like `print`) |
| `RAISE EXCEPTION` | Stop with an error (like `raise`) |

📌 **Remember:** PL/pgSQL = SQL + variables + `IF` + loops + errors.

---

## Step 5 — `RETURN QUERY` and try / except

❓ How do we validate inputs, then return rows? How do we catch an error?

▶️ **Run**

```sql
CREATE OR REPLACE FUNCTION get_payments_checked(p_payer text, p_limit int DEFAULT 5)
RETURNS TABLE (txn_id bigint, txn_ts timestamp, amount numeric,
               status text, merchant_name text)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_limit NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'p_limit must be 1..100, got %', p_limit;
    END IF;
    RETURN QUERY SELECT * FROM get_payments(p_payer, p_limit);
    IF NOT FOUND THEN
        RAISE NOTICE 'No payments for %', p_payer;
    END IF;
END;
$$;

SELECT * FROM get_payments_checked('u1000@bank', 3);    -- 3 rows
SELECT * FROM get_payments_checked('u9950@bank');       -- NOTICE, 0 rows
SELECT * FROM get_payments_checked('u1000@bank', 500);  -- ERROR

CREATE OR REPLACE FUNCTION safe_summary(p_payer text)
RETURNS text LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN payment_summary(p_payer);
EXCEPTION
    WHEN others THEN
        RETURN 'error: ' || SQLERRM;
END;
$$;

SELECT safe_summary('nobody@bank');
```

👀 **See**

```text
NOTICE:  No payments for u9950@bank
ERROR:  p_limit must be 1..100, got 500
 error: Unknown payer: nobody@bank          <- caught: no ERROR
```

- `RETURN QUERY` adds rows to the output. The function ends at `END`.
- `EXCEPTION WHEN others` catches any error. `SQLERRM` = the error message.

📌 **Remember:** validate inputs early; catch errors only where you can do something useful.

---

## Step 6 — Volatility: a promise to the planner

❓ What does `STABLE` mean, and why does it matter?

| Label | Promise | Examples |
|---|---|---|
| `IMMUTABLE` | Same input → same output, **forever**. Reads no tables | `upper()`, maths, `clean_name()` |
| `STABLE` | Same output **within one query**. May read tables | `now()`, `get_payments()` |
| `VOLATILE` (default) | Can change **every call**, or changes data | `random()`, `clock_timestamp()`, `UPDATE`s |

▶️ **Run**

```sql
CREATE OR REPLACE FUNCTION clean_name(p_name text)
RETURNS text LANGUAGE sql IMMUTABLE
AS $$ SELECT lower(trim(p_name)) $$;

-- Search customers by name, typed any way
EXPLAIN (ANALYZE, BUFFERS)
SELECT account_id, holder_name FROM accounts
WHERE clean_name(holder_name) = clean_name('  RAVI Kumar ');

CREATE INDEX idx_acc_clean_name ON accounts (clean_name(holder_name));
-- run the same EXPLAIN again

CREATE OR REPLACE FUNCTION clean_name_stable(p_name text)
RETURNS text LANGUAGE plpgsql STABLE
AS $$ BEGIN RETURN lower(trim(p_name)); END; $$;

CREATE INDEX idx_acc_bad ON accounts (clean_name_stable(holder_name));
```

👀 **See**

```text
-- before the index
 Seq Scan on accounts  (... actual time=0.039..1.898 rows=25 loops=1)
   Filter: (lower(TRIM(BOTH FROM holder_name)) = 'ravi kumar'::text)
   Rows Removed by Filter: 9975
-- after the index
 Bitmap Heap Scan on accounts  (... rows=25 loops=1)
   ->  Bitmap Index Scan on idx_acc_clean_name  (... rows=25 loops=1)
         Index Cond: (lower(TRIM(BOTH FROM holder_name)) = 'ravi kumar'::text)
 Execution Time: 0.034 ms
-- the STABLE one
ERROR:  functions in index expression must be marked IMMUTABLE
```

- An index stores results **in advance**, so only `IMMUTABLE` functions are allowed.
- **Danger:** marking a function `IMMUTABLE` when it reads a table, or uses `now()`. The index keeps **old answers** and queries return wrong rows, with no error.

📌 **Remember:** label honestly. When unsure, `STABLE` for reads, `VOLATILE` for writes.

---

## Step 7 — A function on the column hides the index

❓ `idx_txn_payer` exists. Will both queries use it properly?

🤔 **Predict:** which one is fast?

▶️ **Run**

```sql
EXPLAIN (ANALYZE, BUFFERS)          -- A: function on the COLUMN
SELECT count(*) FROM transactions
WHERE clean_name(payer_account) = 'u1000@bank';

EXPLAIN (ANALYZE, BUFFERS)          -- B: function on the VALUE
SELECT count(*) FROM transactions
WHERE payer_account = clean_name('  U1000@BANK ');
```

👀 **See**

```text
-- A
   ->  Index Only Scan using idx_txn_payer on transactions  (... rows=103 loops=1)
         Filter: (lower(TRIM(BOTH FROM payer_account)) = 'u1000@bank'::text)
         Rows Removed by Filter: 999897
 Execution Time: 187.237 ms
-- B
   ->  Index Only Scan using idx_txn_payer on transactions  (... rows=103 loops=1)
         Index Cond: (payer_account = 'u1000@bank'::text)
         Buffers: shared hit=4
 Execution Time: 0.029 ms
```

- A reads **all 1,000,000** index entries and runs the function on each one: `Filter`, no `Index Cond`.
- B runs the function **once** on the value, then searches the index: `Index Cond`.
- Same answer (103). **187 ms vs 0.03 ms.**

📌 **Remember:** put the function on the **value**, not on the column. (Or build an expression index, Step 6.)

---

## Step 8 — Row-by-row loop vs one statement

❓ Build a summary row (payments, amount paid) for **every** account.

🤔 **Predict:** loop of 10,000 small queries, or one big query: which wins?

▶️ **Run** (both inside `BEGIN ... ROLLBACK`, with `\timing on`)

```sql
-- A: a loop, 1 query + 1 INSERT per account (10,000 times)
FOR r IN SELECT account_id FROM accounts LOOP
    SELECT count(*), coalesce(sum(amount), 0) INTO v_count, v_paid
    FROM transactions
    WHERE payer_account = r.account_id AND status = 'SUCCESS';
    INSERT INTO customer_totals VALUES (r.account_id, v_count, v_paid);
END LOOP;

-- B: one statement for all 10,000 accounts
INSERT INTO customer_totals
SELECT a.account_id, count(t.txn_id), coalesce(sum(t.amount), 0)
FROM accounts a
LEFT JOIN transactions t
       ON t.payer_account = a.account_id AND t.status = 'SUCCESS'
GROUP BY a.account_id;
```

👀 **See**

```text
DO            Time: 644.287 ms     -- A: loop
INSERT 0 10000 Time: 246.488 ms     -- B: set-based
```

- Same 10,000 result rows. The loop is **~2.6× slower**, and that's **with** an index.
- Without `idx_txn_payer`, the loop would scan the whole table **10,000 times**.
- One statement lets the planner choose the best plan (one scan + hash join) for all rows at once.

📌 **Remember:** think in **sets**, not loops. Loop only when each row truly needs different logic.

---

## Step 9 — Plan caching: one plan for every value?

❓ Functions and `PREPARE`d statements can reuse a saved plan. Is one plan good for every value?

▶️ **Run**

```sql
SET max_parallel_workers_per_gather = 0;
CREATE INDEX idx_txn_status ON transactions (status);

PREPARE by_status(text) AS
    SELECT count(*), sum(amount) FROM transactions WHERE status = $1;

SET plan_cache_mode = force_custom_plan;          -- plan made for the actual value
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('PENDING');
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('SUCCESS');

SET plan_cache_mode = force_generic_plan;         -- one plan for any value
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('PENDING');
EXPLAIN (ANALYZE, BUFFERS) EXECUTE by_status('SUCCESS');
```

👀 **See**

| Mode | Value | Plan | Estimated rows | Pages | Time |
|---|---|---|---|---|---|
| custom | PENDING (1%) | Index Scan | 10,733 | 6,946 | 5.2 ms |
| custom | SUCCESS (94%) | Seq Scan | 941,100 | 12,606 | 126 ms |
| generic | PENDING | Bitmap Heap Scan, `status = $1` | **333,333** | 6,946 | 6.1 ms |
| generic | SUCCESS | Bitmap Heap Scan, `status = $1` | **333,333** | 13,401 | 138 ms |

- **Custom plan:** built for the real value. Different value → different plan.
- **Generic plan:** built once with `$1`, without knowing the value. It guesses ⅓ of rows (3 statuses), so it picks one middle plan for all.
- Default mode `auto`: 5 custom plans first, then a generic plan **if** it looks just as cheap.
- PL/pgSQL functions cache the plans of their queries the same way.

📌 **Remember:** skewed data + saved plans = a plan that is wrong for some values. Test busy **and** rare values.

---

## Step 10 — Procedures: `CALL`, and `COMMIT` in batches

❓ Expire old PENDING payments in batches of 2,000, saving after each batch.

▶️ **Run** (on a copy table `pending_queue`, so real data is not changed)

```sql
CREATE TABLE pending_queue AS
SELECT txn_id, status, txn_ts FROM transactions WHERE status = 'PENDING';

CREATE OR REPLACE PROCEDURE expire_pending(p_before timestamp, p_batch int DEFAULT 2000)
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows int;  v_batch int := 0;
BEGIN
    LOOP
        UPDATE pending_queue SET status = 'EXPIRED'
        WHERE txn_id IN (SELECT txn_id FROM pending_queue
                         WHERE status = 'PENDING' AND txn_ts < p_before
                         LIMIT p_batch);
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        EXIT WHEN v_rows = 0;
        v_batch := v_batch + 1;
        COMMIT;                                  -- save this batch now
        RAISE NOTICE 'batch %: % rows expired', v_batch, v_rows;
    END LOOP;
END;
$$;

CALL expire_pending('2026-03-01');
SELECT status, count(*) FROM pending_queue GROUP BY status ORDER BY status;

CREATE OR REPLACE FUNCTION try_commit() RETURNS void
LANGUAGE plpgsql AS $$ BEGIN COMMIT; END; $$;
SELECT try_commit();
```

👀 **See**

```text
NOTICE:  batch 1: 2000 rows expired
NOTICE:  batch 2: 2000 rows expired
NOTICE:  batch 3: 2000 rows expired
NOTICE:  batch 4: 651 rows expired
 EXPIRED |  6651
 PENDING |  3328
ERROR:  invalid transaction termination
```

| | Function | Procedure |
|---|---|---|
| Called with | `SELECT f(...)` | `CALL p(...)` |
| Returns | a value or rows | nothing (or OUT params) |
| `COMMIT` inside | ❌ not allowed | ✅ allowed |
| Use for | calculations, lookups | batch jobs, maintenance |

- Batches keep each transaction small: short locks, and a crash loses only one batch.
- `CALL` with `COMMIT` inside fails if you wrap it in your own `BEGIN ... ROLLBACK`.

📌 **Remember:** function = returns an answer. Procedure = does a job, and may commit as it goes.

---

## Step 11 — Good practice: name parameters `p_`

❓ What goes wrong when a parameter has the same name as a column?

▶️ **Run**

```sql
CREATE FUNCTION count_payments(payer_account text)
RETURNS bigint LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN (SELECT count(*) FROM transactions
            WHERE payer_account = payer_account);    -- column or parameter?
END;
$$;
SELECT count_payments('u1000@bank');

DROP FUNCTION count_payments(text);
CREATE FUNCTION count_payments(p_payer text)
RETURNS bigint LANGUAGE sql STABLE STRICT
AS $$ SELECT count(*) FROM transactions WHERE payer_account = p_payer $$;

SELECT count_payments('u1000@bank');    -- 103
SELECT count_payments(NULL);            -- NULL: STRICT skips the query
```

👀 **See**

```text
ERROR:  column reference "payer_account" is ambiguous
DETAIL:  It could refer to either a PL/pgSQL variable or a table column.
 103
          <- empty cell = NULL
```

- `p_` for parameters, `v_` for variables: no clashes, easy to read.
- `STRICT`: any `NULL` input → returns `NULL` immediately, without running the body.

📌 **Remember:** prefix names, and qualify columns with the table alias (`t.payer_account`).

---

## Lab 06 summary

| You saw | It means |
|---|---|
| `LANGUAGE sql` function, plan shows `Index Cond` | Simple SQL functions are inlined: no extra cost |
| `Function Scan on ...` | PL/pgSQL body is hidden: EXPLAIN its inner query yourself |
| `functions in index expression must be marked IMMUTABLE` | Only `IMMUTABLE` functions can be indexed |
| `Filter: (lower(...payer_account...))` | Function on the column: index cannot search |
| Loop 644 ms vs one statement 246 ms | Set-based beats row-by-row |
| `status = $1`, `rows=333333` | Generic plan: one plan for all values |
| `invalid transaction termination` | Only procedures can `COMMIT` |

### Function checklist

- [ ] Can it be **one SQL statement**? Then do that, not a loop.
- [ ] Correct **volatility** label?
- [ ] Parameters named `p_...`, columns qualified?
- [ ] Inputs **validated**, clear `RAISE EXCEPTION` messages?
- [ ] Function on the **value** side of `WHERE`, not the column?
- [ ] Tested with a **busy** and a **rare** value?
- [ ] `SECURITY DEFINER`? Only with care: it runs with the **owner's** rights. Set `search_path` too.

---

## Try it yourself

- **T1.** Write `merchant_payments(p_merchant text, p_limit int DEFAULT 10)` returning the latest payments **received** by a merchant. Call it for `'merchant7'`.
- **T2.** Extend `payment_summary`: level `'VIP'` when the SUCCESS amount is above Rs 5,000,000. Test `u42@bank` and `u1000@bank`.
- **T3.** Which volatility, and why?
  - a) `gst(amount)` returns `amount * 0.18`
  - b) `payments_today(p_payer)` counts payments where `txn_ts >= current_date`
  - c) `new_upi_ref()` returns a random 12-character reference
- **T4.** Rewrite as **one** statement (no loop):
  ```sql
  FOR r IN SELECT account_id FROM accounts WHERE segment = 'PREMIUM' LOOP
      UPDATE accounts SET city = upper(city) WHERE account_id = r.account_id;
  END LOOP;
  ```
- **T5.** `EXPLAIN (ANALYZE) SELECT * FROM get_payments_checked('u1000@bank');`
  - Can you see the index? How would you check the inner plan instead?

---

## Common mistakes

- ❌ Loops over rows for work one `UPDATE` / `INSERT ... SELECT` can do
- ❌ Every function left as `VOLATILE` (the default), or `IMMUTABLE` on a function that reads tables
- ❌ `WHERE my_func(column) = value`: index cannot search
- ❌ Parameter named like a column → "ambiguous" error, or worse, a silent wrong result
- ❌ `COMMIT` inside a function → only procedures can commit
- ❌ Trusting EXPLAIN of `Function Scan`: it hides the real plan
- ❌ Testing with one value only: saved plans can be bad for skewed values

---

## Quick quiz

1. How do you call a function with named arguments?
2. Which volatility can be used in an index?
3. `WHERE clean_name(payer_account) = 'u1000@bank'`: why is it slow, and how do you fix it?
4. Can a function `COMMIT`? Can a procedure?
5. A plan shows `status = $1`. What kind of plan is it?

**Next:** you have finished the workshop labs. Use the cheat sheet in `handouts/` at work.
