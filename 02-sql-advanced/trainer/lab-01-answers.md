# Lab 01 — Trainer Answer Key

**Not for participants.** Reference numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42).
Rows, pages and plan shapes are identical on every laptop; milliseconds are not.

## Key reference numbers

| Item | Value |
|---|---|
| `transactions` pages / size / rows per page | 12,606 / 98 MB / 79 |
| Seq Scan cost for one payer | 25,106 (= 12,606 + 10,000 + 2,500) |
| `u1000@bank`: estimate / actual rows | 98 / 103 |
| Seq Scan: rows removed / pages / time | 999,897 / 12,606 / ~36 ms |
| FAILED rows | 48,998 (WEB 22,708 / APP 17,875 / UPI_QR 8,415) |
| PK lookup `txn_id = 500000` | Index Scan, 7 pages, ~0.01 ms |
| After `idx_txn_payer`: pages / time | 106 (3 index + 103 heap) / ~0.1 ms |
| Parallel version of Step 6 | ~20 ms vs ~46 ms, `loops=3`, 16,333 × 3 rows |

## Try it yourself

**T1: busy payer `u42@bank`**
- Bitmap Heap Scan, **10,216 rows**, **Heap Blocks: exact=7,017**, ~11 ms.
- Slower than `u1000@bank`: 100× more rows spread over 7,017 of the 12,606 pages (more than half the table).
- Teaching point: an index helps when it lets us **skip** most pages. Here it skips less than half. This sets up Lab 02 (selectivity).

**T2: FAILED + WEB**
- Estimate **≈ 7,592 rows**, actual **22,708**: about **3× too low**.
- Why: the planner assumes status and channel are independent (5% × 15% = 0.75%). In reality WEB fails far more often (15%).
- Fixed in Lab 04 with `CREATE STATISTICS`. Only plant the idea here.

**T3: Step 6**
- Most rows: **Seq Scan** reads 1,000,000, outputs 48,998.
- Fewest: **HashAggregate** and **Sort**, 3 rows each.

**T4: merchants**
- `Index Scan using merchants_pkey`. `merchant_account` is the primary key, and PostgreSQL creates an index for every primary key (and unique constraint) automatically.

## Quiz answers

1. No. Only `EXPLAIN ANALYZE` runs it.
2. `rows=98` (the part without "actual") is the guess.
3. Every page of the table was read, i.e. a full scan; all were already in cache (`hit`).
4. The **most indented** line produces rows first; data flows upward.
5. 500 × 3 = **1,500**.

## Teaching tips

- **Before Step 2**, ask the room: "1 million rows, find 103. How would *you* do it with a printed register?" Get to "flip every page" vs "use the index at the back".
- **Step 3** is optional for weaker groups. The point is "cost is arithmetic, not magic".
- **Step 5**: write **12,606** on the whiteboard. Every later comparison refers back to it.
- **Step 8**: let learners predict "Index Scan" first. When they see "Bitmap", explain with the 103-pages picture (slide).
- **Step 9**: emphasise "parallel = more workers, same total work". It is not a tuning fix.
- If a learner's plan differs: check (a) they ran `reset.sql`, (b) `max_parallel_workers_per_gather`, (c) `ANALYZE` was run.
