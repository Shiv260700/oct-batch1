# Lab 02 — Trainer Answer Key

**Not for participants.** Reference numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42), parallel query off.
Rows, pages and plan shapes match on every laptop. Milliseconds and estimated `rows=` vary a little (ANALYZE samples randomly).

## Key reference numbers

| Step | Item | Value |
|---|---|---|
| 1 | SUCCESS / FAILED / PENDING | 941,023 / 48,998 / 9,979 (94.1 / 4.9 / 1.0 %) |
| 2 | `u1000@bank` with payer index | 103 rows, 103 heap pages, ~0.15 ms |
| 2 | `u42@bank` with payer index | 10,216 rows, **7,017** heap pages, ~13 ms |
| 3 | `status = 'PENDING'` | Index Scan, 9,979 rows |
| 3 | `status = 'SUCCESS'` | Seq Scan, 12,606 pages, ~100 ms |
| 3 | Forced index for SUCCESS | Bitmap Heap Scan, 12,606 heap + 792 index pages, ~96 ms (no gain) |
| 4 | Latest 10 of `u42`: payer index only | Sort (top-N heapsort) over 10,216 rows, 7,029 pages, ~6 ms |
| 4 | Latest 10 of `u42`: `(payer_account, txn_ts DESC)` | Limit → Index Scan, no Sort, 13 pages, ~0.03 ms |
| 5 | Wrong order `(txn_ts DESC, payer_account)` for `u1000` | 661 pages, ~3.6 ms (vs 13 pages, ~0.03 ms) |
| 6 | 15 March 2026 | **11,186** rows. Cast: Seq Scan 12,606 pages ~55 ms. Range: Index Only Scan 34 pages ~1 ms |
| 7 | `lower(holder_name) = 'ravi kumar'` | 25 rows. Plain index ignored (Seq Scan, 9,975 removed); expression index → Bitmap scan |
| 8 | Failed queue, before partial index | Index Scan Backward on `idx_txn_ts`, Rows Removed by Filter 298 |
| 8 | Partial index size | 1,088 kB vs 21 MB (full `txn_ts` index) |
| 9 | Covering index | Index Only Scan, Heap Fetches 0, 4 pages (vs 106 + Sort) |
| 10 | After UPDATE + ROLLBACK | Heap Fetches **206**, 211 pages; after VACUUM: 0, 5 pages |
| 11 | Correlation `txn_ts` / `payer_account` | 1 / ≈ 0 |
| 11 | BRIN vs B-tree size | 24 kB vs 21 MB |
| 11 | BRIN plan for one day | Heap Blocks lossy=256, Rows Removed by Index Recheck 9,129, 261 pages, ~2 ms |
| 12 | Table vs all indexes | 98 MB vs 145 MB |
| 12 | Insert 50,000 rows | no indexes ~21 ms, 632 pages dirtied, 5 MB · 8 indexes ~355 ms, 1,818 dirtied, 14 MB |

**Why 206 heap fetches for 103 rows (Step 10):** `amount` is in the covering index, so the update could not be HOT. Each row got a second (aborted) version *and* a second index entry. The index then has 206 entries for `u1000@bank`, and each must be checked in the table because the visibility-map bits were cleared.

## Try it yourself

**T1: top 5 biggest payments of `u1000@bank`**
```sql
CREATE INDEX idx_txn_payer_amount ON transactions (payer_account, amount DESC);
EXPLAIN (ANALYZE, BUFFERS)
SELECT txn_id, amount, txn_ts FROM transactions
WHERE payer_account = 'u1000@bank' ORDER BY amount DESC LIMIT 5;
```
- Limit → Index Scan using the new index, **no Sort**, 8 pages, ~0.04 ms.
- Same rule as Step 4: equality column first, then the `ORDER BY` column.

**T2: `channel = 'WEB'`**
- 150,612 rows (15%). Plan: Bitmap Heap Scan with **Heap Blocks: exact=12,606**, i.e. every table page, ~46 ms.
- WEB rows are spread over every page, so the index saves no table pages. Not a good standalone index.
- Teaching point: 15% "sounds small" but still touches every page.

**T3: month filter**
```sql
SELECT count(*) FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-02-01' AND txn_ts < TIMESTAMP '2026-03-01';
```
- Both return **311,202**. `date_trunc` version: Seq Scan, 688,798 removed, ~94 ms. Range version: Index Only Scan on `idx_txn_ts`, ~31 ms.

**T4: pending payments with no payee**
```sql
CREATE INDEX idx_txn_pending_no_payee ON transactions (txn_ts)
WHERE status = 'PENDING' AND payee_account IS NULL;
```
- 1,982 rows. Before: Index Scan on `idx_txn_status` + Filter, 7,997 removed, ~6 ms. After: Index Scan on the partial index, ~1.3 ms. Index size **64 kB**.
- Bonus observation: the planner estimates **22** rows but there are 1,982, because it assumes the two conditions are independent (all NULL payees are PENDING). Lab 04 covers this.

## Quiz answers

1. Seq Scan. Reading the table directly is cheaper than index + almost every page.
2. `(payer_account, txn_ts DESC)`.
3. The index stores `txn_ts` values, not `txn_ts::date` values. A function on the column hides it from the index. Rewrite as a half-open range.
4. All columns came from the index and no table page was visited (pages were all-visible).
5. BRIN only works when values follow the physical row order (time-ordered, append-only). It is lossy (rechecks rows) and cannot give ordered output or find single rows precisely.

## Teaching tips

- **Step 1**: write the selectivity table on the board. Every later decision refers back to it.
- **Step 3** is the big "aha": an index that is *not* used is often the planner being smart. Let the room argue before showing the forced plan.
- **Step 5**: use the phone-directory analogy *before* running. Ask "find everyone named Ravi" with a directory sorted by surname.
- **Step 6**: a very common real-world bug. Ask learners to grep their own project's SQL for `::date =`, `DATE(col) =`, `lower(col) =`.
- **Step 10** is optional for weaker groups; the key line is "VACUUM keeps Index Only Scans fast".
- **Step 12**: point at "indexes 145 MB > table 98 MB". Freshers are always surprised.
- If plans differ: check `max_parallel_workers_per_gather = 0` and that `reset.sql` was run (leftover Lab 01 indexes change choices).
