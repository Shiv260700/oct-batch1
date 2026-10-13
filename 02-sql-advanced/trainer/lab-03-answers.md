# Lab 03 — Trainer Answer Key

**Not for participants.** Reference numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42), `max_parallel_workers_per_gather = 0`.
Rows, pages and plan shapes are identical on every laptop; milliseconds are not.

## Key reference numbers

| Step | Item | Value |
|---|---|---|
| 1 | u1000 payments / joined rows | 103 / **102** (1 PENDING payment has NULL payee) |
| 1 | Plan | Nested Loop: Seq Scan outer (12,606 pages) + `merchants_pkey` Index Scan `loops=103` (306 pages), ~41 ms |
| 2 | Joined rows / groups | 998,018 (1,982 NULL payees dropped) / 6 categories |
| 2 | Hash node | `Buckets: 2048  Batches: 1  Memory Usage: 119kB`, ~305 ms |
| 2 | Category totals | UTILITIES 187,341 · FUEL 184,011 · TRAVEL 182,989 · FOOD 148,541 · ELECTRONICS 147,731 · GROCERY 147,405 |
| 3 | Forced Merge Join | Sort 1M rows `external merge Disk: 28664kB`, ~1,382 ms (4.5× slower) |
| 4 | Hyderabad CORPORATE accounts / payments | 48 accounts (47 have paid) / 4,541 payments |
| 4 | Before FK index | Hash Join, 12,699 pages, ~110 ms |
| 4 | After `idx_txn_payer` | Nested Loop, Bitmap scan `loops=48`, 4,760 pages, ~5 ms |
| 4 | Top customer | u7483@bank (Rohan Rao): 116 payments, ₹810,098.02 |
| 5 | Mumbai merchants / PREMIUM accounts | 281 / 1,500 |
| 5 | Join sizes | payments ⨝ Mumbai = 127,121 → ⨝ PREMIUM = 18,397 → 6 groups |
| 6 | ON vs WHERE | 2,000 vs 439 merchants (547 failed payments on 31 Mar) |
| 7 | Pune merchants / paid | 202 / 193 |
| 7 | JOIN+DISTINCT vs EXISTS | 97,662 joined rows, ~22 ms vs Semi Join `rows=1 loops=202`, ~0.7 ms |
| 8 | Never paid | 50 merchants (merchant1951–2000), Nested Loop Anti Join, ~6 ms |
| 8 | PENDING version | NOT EXISTS 155 vs NOT IN 0 |
| 8 | Full NOT IN | cost 30,955,045 (vs 1,012); measured 86 s, 0 rows |
| 9 | work_mem 4MB vs 64kB | `Batches: 1, 626kB` vs `Batches: 8, 81kB` + `temp read/written=3990`; ~297 vs ~364 ms |

## Try it yourself

**T1: Step 1 after `idx_txn_payer`**
- Now a **Hash Join**: Bitmap Index Scan finds the 103 payments (~106 pages); merchants (2,000 rows, 20 pages) go into the hash. ~1 ms instead of ~41 ms.
- Why it changed: the outer side became cheap (index instead of a full scan). With only 2,000 merchants, building a hash once is cheaper than 103 index lookups. **The planner re-prices every plan; adding an index can change the join method.**

**T2: accounts never paid**
```sql
SELECT a.account_id, a.holder_name
FROM accounts a
WHERE NOT EXISTS (SELECT 1 FROM transactions t WHERE t.payer_account = a.account_id);
```
- **100 rows** (u9901–u10000). `Nested Loop Anti Join` with `Index Only Scan using idx_txn_payer ... loops=10000`, ~19 ms.

**T3: zero failed payments on 31 March**
- **1,561** merchants (= 2,000 − 439). Add `HAVING count(t.txn_id) = 0` to version A, or wrap it and filter `failed = 0`.

**T4: NOT IN + IS NOT NULL**
- **Correct** now (50 rows), but the plan is still a `SubPlan` + `Materialize` with cost ~33,394,545: still re-reads ~1M rows per merchant (the 1M-value list is too big for an in-memory hashed subplan with 4MB `work_mem`).
- Better fix: **NOT EXISTS** (correct and an Anti Join, ~6 ms).

## Quiz answers

1. The inner index lookup ran **103 times**, once per outer row.
2. The **smaller** one (here merchants or accounts), so the lookup table fits in memory.
3. **Bad sign:** the hash didn't fit in `work_mem` and spilled to temp files on disk.
4. **No.** Only primary keys and unique constraints get indexes automatically.
5. **NULL** (not true, not false), so a `WHERE` with it keeps no rows.
6. **EXISTS**: it stops at the first match and never produces duplicates.

## Teaching tips

- **Start with the simulators** (slides): Nested Loop, Hash, Merge on 4 payments × 3 merchants. Learners click through; ask them to count comparisons.
- **Step 1**: point at `loops=103` and multiply: 103 × 3 pages = 309 ≈ 306. Then ask "what is the slow part?". Answer: the outer Seq Scan, not the join.
- **Step 1, 102 vs 103**: ask before revealing. It previews Step 8's NULL story.
- **Step 3**: stress `SET LOCAL` + `ROLLBACK`. If someone used plain `SET`, their session keeps hash joins off until `RESET ALL` (or `\i sql/reset.sql`).
- **Step 4**: run `\d transactions` live and read the "Foreign-key constraints" section aloud. Many developers believe FKs are indexed (true in MySQL/InnoDB, not in PostgreSQL).
- **Step 6**: have learners run version B first and "ship" the report; then reveal 1,561 missing merchants. Bugs like this are a correctness issue, not a speed issue, but they show up in tuning work all the time.
- **Step 8D**: insist on `EXPLAIN` only. If someone runs it with `ANALYZE`, press **Ctrl+C** to cancel.
- **Step 9**: `work_mem` is per sort/hash **node, per connection**. 100 connections × 4 hash nodes × 256MB would exhaust RAM.
- If a learner's plan differs: check (a) `reset.sql` was run, (b) parallel is off, (c) indexes from earlier steps exist (`\d transactions`).
