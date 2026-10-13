# Lab 06 — Trainer Answer Key

**Not for participants.** Reference numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42), run as a **non-superuser database owner** (like `labuser`).
Rows, pages and plan shapes match on every laptop; milliseconds do not.

## Key reference numbers

| Item | Value |
|---|---|
| Latest payment of `u1000@bank` | txn 998042, 2026-03-31 19:44:51, Rs 28,471.72, Fresh Travel #1293 |
| `get_payments('u1000@bank')` plan | Inlined: Limit → Sort (top-N) → Hash Left Join → Bitmap scan on `idx_txn_payer`; ~0.4 ms, 126 pages |
| `payment_summary` | u1000: 103 / 4 failed / Rs 724,985.83 / OK · u7501: 109 / 15 / Rs 270,420.11 / CHECK · u9950: NEW |
| Name search "ravi kumar" | 25 accounts · Seq Scan 93 pages → Bitmap via `idx_acc_clean_name` |
| Function on column vs value (count = 103) | ~187 ms, `Filter`, 999,897 removed · vs ~0.03 ms, `Index Cond`, 4 pages |
| Loop vs set-based (10,000 accounts) | ~644 ms vs ~246 ms (≈ 2.6×) |
| `by_status` custom PENDING / SUCCESS | Index Scan, est 10,733, 6,946 pages · Seq Scan, est 941,100, 12,606 pages |
| `by_status` generic (both values) | Bitmap Heap Scan, `status = $1`, est **333,333**; SUCCESS reads 13,401 pages |
| `expire_pending('2026-03-01')` | 4 batches (2000/2000/2000/651) → EXPIRED 6,651 · PENDING 3,328 |

## Notes on the demos

- **Step 3 inlining:** a `LANGUAGE sql`, `STABLE`/`IMMUTABLE`, single-`SELECT`, non-`SECURITY DEFINER`, non-`STRICT` set-returning function is inlined. If learners add `STRICT` or `SECURITY DEFINER` to `get_payments`, the plan becomes `Function Scan`. That's a good extra demo.
- **Step 6, STABLE index error:** the STABLE demo function is deliberately PL/pgSQL. A STABLE `LANGUAGE sql` wrapper around `lower(trim())` gets **inlined** before the index check, and the index is created without error. Don't "simplify" it back to SQL.
- **Step 7:** on a freshly loaded database the planner reads the whole **index** (Index Only Scan + `Filter`) instead of the table. Still 999,897 rows removed, still no `Index Cond`. If someone sees a `Seq Scan` instead (visibility map not set), it is the same lesson.
- **Step 8:** the gap grows without the payer index (10,000 full scans: do **not** run that live). Point at the 2.6× **with** a perfect index.
- **Step 9:** with `auto` mode, after 6 runs of `by_status('PENDING')`, `pg_prepared_statements` shows `custom_plans = 6, generic_plans = 0`: PostgreSQL noticed the generic plan would cost more (22,155 vs 6,991) and kept custom plans. Generic plans hurt most when the cheap custom plan and the generic plan look similar in cost but differ for skewed values.
- **auto_explain:** `LOAD 'auto_explain'` fails for `labuser` (`access to library "auto_explain" is not allowed`). As a superuser you can demo:
  ```sql
  LOAD 'auto_explain';
  SET auto_explain.log_min_duration = 0;
  SET auto_explain.log_nested_statements = on;
  SET client_min_messages = log;      -- show the plan in psql
  SELECT * FROM get_payments_checked('u1000@bank');
  ```
  For participants, the practical method is: **copy the inner query, replace parameters with values, EXPLAIN it.**
- **Step 10:** `CALL expire_pending(...)` inside `BEGIN; ... ROLLBACK;` fails with `invalid transaction termination`. That is why the step uses a copy table.

## Try it yourself

**T1: merchant_payments**
```sql
CREATE OR REPLACE FUNCTION merchant_payments(p_merchant text, p_limit int DEFAULT 10)
RETURNS TABLE (txn_id bigint, txn_ts timestamp, payer_account text,
               amount numeric, status text)
LANGUAGE sql STABLE
AS $$
    SELECT t.txn_id, t.txn_ts, t.payer_account, t.amount, t.status
    FROM transactions t
    WHERE t.payee_account = p_merchant
    ORDER BY t.txn_ts DESC
    LIMIT p_limit;
$$;
SELECT * FROM merchant_payments('merchant7');
```
- `merchant7` received 4,397 payments; the latest is txn 999934 (u838@bank, Rs 798.89).
- No index on `payee_account` after `reset.sql`, so this is a Seq Scan. Ask: which index would help? (`(payee_account, txn_ts DESC)`, from Lab 02.)

**T2: VIP level**
- Add before the `CHECK` branch: `ELSIF v_amount > 5000000 THEN v_level := 'VIP';`
- Only the 3 busy payers qualify: u42 (Rs 43,487,072.23), u43 (Rs 42,121,109.23), u44 (Rs 44,084,516.29). u1000 stays `OK`.
- Discuss branch order: `IF` stops at the first true condition.

**T3: volatility**
- a) `gst(amount)`: **IMMUTABLE**. Pure maths, no tables, no time.
- b) `payments_today(p_payer)`: **STABLE**. Reads a table, and `current_date` is fixed within a query.
- c) `new_upi_ref()`: **VOLATILE**. A different result every call; must not be cached.

**T4: set-based**
```sql
UPDATE accounts SET city = upper(city) WHERE segment = 'PREMIUM';   -- 1,500 rows
```
- Run it inside `BEGIN; ... ROLLBACK;` to keep the data unchanged.

**T5: PL/pgSQL is a black box**
- Plan shows only `Function Scan on get_payments_checked (... rows=5 loops=1)`, with no index visible.
- Check the inner plan: `EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM get_payments('u1000@bank', 5);` (inlined), or paste the query with literal values.

## Quiz answers

1. `get_payments(p_limit => 3, p_payer => 'u42@bank')`
2. Only `IMMUTABLE`.
3. The function runs on all 1,000,000 values and the index cannot search (`Filter`, not `Index Cond`). Fix: apply the function to the **value** (`payer_account = clean_name('...')`), or create an expression index on `clean_name(payer_account)`.
4. Function: no (`invalid transaction termination`). Procedure: yes, when called with `CALL` outside an explicit transaction block.
5. A **generic** plan: built without knowing the parameter value.

## Teaching tips

- Open with the Python table: freshers relax when they see `def` ↔ `CREATE FUNCTION`.
- **Step 3** is the "aha": functions are not slow by nature. The inner query decides.
- **Step 6:** tell the stale-index story. Someone marks `get_category(merchant)` IMMUTABLE and indexes it; a merchant changes category; the index still returns the old category. No error, just wrong answers.
- **Step 8:** ask the room first: "Who has written a loop over rows in Python + SQL?" Most have. Set-based thinking is the biggest habit change of this lab.
- **SECURITY DEFINER:** one sentence only. It runs with the owner's privileges, so always `SET search_path` on it and grant `EXECUTE` narrowly.
- If a learner's output differs: check they ran `reset.sql` and Step 0's index, and that `\set ON_ERROR_STOP off` is active (otherwise the file stops at the first intended error).
