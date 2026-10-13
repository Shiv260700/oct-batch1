# Lab 04 — Trainer Answer Key

**Not for participants.** Reference numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42), `max_parallel_workers_per_gather = 0`, `jit = off`, warm cache.
Rows, pages and plan shapes are identical on every laptop; milliseconds are not. **Statistics estimates vary slightly** (ANALYZE samples randomly).

## Key reference numbers

| Item | Value |
|---|---|
| Correlated subquery, 20 merchants, no index | 20 loops × full scan, ~252,000 pages, ~830 ms |
| Correlated subquery, all 2,000, no index | cost 50,214,620; ~82 s (do **not** run with ANALYZE) |
| Group once + LEFT JOIN, all 2,000 | 1 scan, 1,951 groups (incl. NULL payee), ~162 ms |
| Correlated + `idx_txn_payee` | Index Only Scan × 2,000 loops, ~88 ms |
| Equivalence: LEFT JOIN rewrite / INNER JOIN rewrite | `0 \| 0` / `50 \| 0` |
| Category report: join-then-group / group-then-join | 998,018 rows joined, ~310 ms / 1,950 rows joined, ~195 ms |
| Payments with NULL payee (dropped by inner join) | 1,982 |
| CTE `merchant7`: default / MATERIALIZED | 2.7 ms (Bitmap on idx_txn_payee, 4,397 rows) / 193 ms (CTE Scan, 1,950 removed) |
| Latest per payer: row_number / DISTINCT ON | 9,900 rows; both sort 1M rows, external merge 48 MB, ~1.15 s |
| Latest 3 per merchant: LATERAL + `idx_txn_payee_ts` | 5,850 rows, 2,000 loops, ~17 ms |
| `u42@bank` payments | 10,216 |
| OFFSET 9000 LIMIT 20 | 7,082 pages, ~7.3 ms |
| Keyset cursor (row 9,000) | `2026-01-11 05:57:53`, `114483` |
| Keyset page | 15 pages, ~0.02 ms |
| FAILED + WEB: estimate before / after stats / actual | ~7,000–7,600 / ~23,000–24,000 / 22,708 |

## Try it yourself

**T1: biggest payment per account**

```sql
SELECT a.account_id, x.biggest_payment
FROM accounts a
LEFT JOIN (SELECT payer_account, max(amount) AS biggest_payment
           FROM transactions
           GROUP BY payer_account) x
       ON x.payer_account = a.account_id;
```

- Template result: `0 | 0`.
- The 100 accounts that never paid must get **NULL**, not 0: `max()` of no rows is NULL. Adding `COALESCE(..., 0)` makes the proof fail (`100 | 100`).
- Teaching point: `COALESCE(count, 0)` is right for counts; it is wrong for max/min/avg.

**T2: latest 2 per payer**
- `WHERE rn <= 2` → **19,800 rows** (9,900 payers × 2).
- `DISTINCT ON` keeps exactly **one** row per group; it cannot return 2.

**T3: MATERIALIZED for merchant1 vs merchant1500**
- Same time (~150–190 ms): the whole CTE (all 1,951 groups) is built first, whatever we filter on afterwards. merchant1 has 22,598 payments, merchant1500 has 298. It makes no difference.
- (merchant1951–2000 never received payments: they return 0 rows.)

**T4: next keyset page**

```sql
SELECT txn_ts AS last_ts, txn_id AS last_id
FROM transactions
WHERE payer_account = 'u42@bank'
  AND (txn_ts, txn_id) < (:'last_ts', :last_id)
ORDER BY txn_ts DESC, txn_id DESC
LIMIT 1 OFFSET 19 \gset
```

- New cursor = row 9,020: `2026-01-11 01:44:50`, `112478`. Rerun Step 8b.

## Quiz answers

1. The subquery ran 2,000 times, once per outer row.
2. No. 50 rows exist only in the original: the rewrite lost the merchants without payments (INNER instead of LEFT JOIN).
3. Default: the filter is pushed **inside** the CTE, so only merchant7's 4,397 rows are read via the index. MATERIALIZED: all 1M rows are aggregated first, then 1,950 groups are thrown away.
4. Keyset: it seeks straight to the cursor in the index (15 pages). OFFSET must read and discard 9,000 rows (7,082 pages).
5. The columns are related; `CREATE STATISTICS ... (mcv) ON status, channel` + `ANALYZE`.

## Teaching tips

- **Step 1**: before running, ask "how many times will the subquery run?" Most freshers say "once".
- **Never** demo the full 2,000-merchant correlated query with `ANALYZE` (~80 s). Use the `EXPLAIN`-only cost.
- **Step 4** is the heart of the lab. Make the INNER JOIN bug land: "faster and wrong is worse than slow and right".
- **Step 5**: the gain (~310 → ~195 ms) is moderate. That is the honest result; say pre-aggregation helps most when the join is expensive or the grouped result is tiny.
- **Step 7**: both versions spill to disk (`external merge`). Optional extension: `SET work_mem = '64MB'` and rerun: the sort becomes in-memory.
- **Step 8**: ask "what does the user see if a new payment arrives between page clicks?" OFFSET shifts rows; keyset does not.
- **Step 9**: estimates differ per laptop (random sample). Focus on "7k vs 22k", not exact digits. Plan changes caused by statistics come back in Lab 03 (join choice).
