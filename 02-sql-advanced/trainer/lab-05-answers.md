# Lab 05 — Trainer Answer Key: The Slow Dashboard

**Not for participants.** Numbers come from PostgreSQL 17 with `sql/00_setup.sql` (seed 0.42), measured twice.
Rows, pages and plan shapes match on every laptop; milliseconds vary (often by 2× on busy laptops).

## The planted problems at a glance

| Panel | Planted problem(s) | Lab | Type |
|---|---|---|---|
| Q1 Daily summary | `txn_ts::date` wraps the column + no index on `txn_ts` | 02 | Slow |
| Q2 Merchants to call | Correlated sub-query runs 311× + FK `payee_account` unindexed | 04, 03 | Very slow |
| Q2 trap | "Fast" inner `JOIN` drops the 8 ₹0 merchants | 03 | **Wrong after fix** |
| Q3 Dormant merchants | `NOT IN` + 1,982 `NULL` payees → returns 0 rows | 03 | **Wrong** and slow |
| Q4 History page 251 | FK `payer_account` unindexed + deep `OFFSET 5000` | 02, 04 | Slow |
| Q4 bonus | Inner `JOIN` hides 17 PENDING payments with no payee | 03 | Hidden data |

## Final scoreboard (reference)

| Panel | Baseline | Best version | Gain |
|---|---|---|---|
| Q1 | 30 ms · 12,720 pages | **2.9 ms · 181 pages** | ~10× · 70× fewer pages |
| Q2 | 11,400 ms · **3,920,486 pages** | **23 ms · 1,854 pages** | ~500× |
| Q3 | 5,050 ms · **0 rows (wrong)** | **10 ms · 6,021 pages · 50 rows** | correct + ~500× |
| Q4 | 26 ms · 12,894 pages | **0.1 ms · 72 pages** | ~260× |
| **Dashboard** | **≈ 16.5 s · ≈ 3.96 M pages** | **≈ 36 ms · ≈ 8,100 pages** | **≈ 450×** |

- Index storage added for the best version: `idx_txn_ts` 21 MB + `idx_txn_payee_cover` 47 MB + `idx_txn_payer_ts` 47 MB = **115 MB on a 98 MB table**. Use this in the "what did it cost?" discussion.

---

## Q1 · Daily summary

**Baseline:** Parallel Seq Scan, `Filter: ((txn_ts)::date = '2026-03-15'::date)`, `Rows Removed by Filter: 329605` × 3, **12,720 pages, ~30 ms**.

**The key teaching moment: neither fix works alone.**

| Version | Plan | Pages | ms |
|---|---|---:|---:|
| Baseline (cast, no index) | Parallel Seq Scan | 12,720 | 30 |
| Rewrite only (range, no index) | Parallel Seq Scan | 12,622 | 20 |
| Index only (`idx_txn_ts`, still cast) | Parallel Seq Scan | 12,720 | 24 |
| **Index + range** | **Index Scan using idx_txn_ts** | **178** | **2.4–2.9** |
| Bonus B1: BRIN + range | Bitmap Heap Scan (lossy=256) | 261 | 3.1 |

```sql
CREATE INDEX idx_txn_ts ON transactions (txn_ts);

SELECT channel, count(*) AS payments, sum(amount) AS total_amount,
       count(*) FILTER (WHERE status = 'FAILED') AS failed
FROM transactions
WHERE txn_ts >= TIMESTAMP '2026-03-15'
  AND txn_ts <  TIMESTAMP '2026-03-16'
GROUP BY channel
ORDER BY channel;
```

- Answer: APP 6,677 / 30,663,138.25 / 184 · UPI_QR 2,810 / 12,875,227.24 / 80 · WEB 1,699 / 7,209,859.75 / 257. Total 11,186 rows.
- H2 check: **0 / 0**.
- **B1 BRIN:** `CREATE INDEX ... USING brin (txn_ts)` is **24 kB** vs 21 MB for the B-tree, at 261 vs 178 pages. Works because rows are stored in time order (correlation = 1).
- Also accepted: an expression index `ON transactions ((txn_ts::date))` keeps the original SQL. Ask: "which is easier to reuse for *other* date ranges?" (the plain index).

**Ask the room:** "You added the index and nothing changed. Is the index broken?" No: the query hides the column inside a cast.

---

## Q2 · Grocery merchants to call

**Baseline:** `Seq Scan on merchants` (311 GROCERY rows) → `SubPlan 1` → `Seq Scan on transactions ... loops=311`.
- 311 × 12,606 = **3,920,486 pages**. **~11.4 s**, the slowest panel by far.
- Bottom-10 answer: 8 merchants with **0** (merchant1952, 1970, 1978, 1981, 1982, 1983, 1991, 1992), then merchant1919 (571,641.54), merchant1375 (831,572.89).

| Version | Plan | Pages | ms | Correct? |
|---|---|---:|---:|---|
| Baseline | SubPlan Seq Scan, loops=311 | 3,920,486 | 11,400 | ✅ |
| ❌ Trap: inner `JOIN` + `GROUP BY` | Hash Join, Parallel Seq Scan | 12,688 | 65 | **❌ 8 rows differ** |
| Option A: group once + `LEFT JOIN` | Hash Right Join + GroupAggregate | 12,642 | 75–83 | ✅ |
| Option B1: plain index on `payee_account` | SubPlan Bitmap Heap Scan, loops=311 | 143,156 | 130–210 | ✅ |
| **Option B2: covering index** | **SubPlan Index Only Scan, loops=311** | **1,854** | **20–23** | ✅ |

**The trap (most important correctness moment of the course):**

```sql
-- FAST BUT WRONG: drops merchants that have no SUCCESS payments
SELECT m.merchant_account, m.merchant_name, sum(t.amount) AS revenue
FROM merchants m
JOIN transactions t ON t.payee_account = m.merchant_account AND t.status = 'SUCCESS'
WHERE m.category = 'GROCERY'
GROUP BY m.merchant_account, m.merchant_name
ORDER BY revenue, m.merchant_account
LIMIT 10;
```

- Returns merchant1919, 1375, 1888 … The 8 ₹0 merchants (the ones sales must call) are gone.
- H2 against `lab05_q2_old`: **8 / 8** rows differ. Full-list check (311 rows): old minus trap = 8.

**Option A: rewrite**

```sql
SELECT m.merchant_account, m.merchant_name, coalesce(r.revenue, 0) AS revenue
FROM merchants m
LEFT JOIN (SELECT payee_account, sum(amount) AS revenue
           FROM transactions
           WHERE status = 'SUCCESS'
           GROUP BY payee_account) r
       ON r.payee_account = m.merchant_account
WHERE m.category = 'GROCERY'
ORDER BY revenue, m.merchant_account
LIMIT 10;
```

**Option B2: index (keeps the original SQL)**

```sql
CREATE INDEX idx_txn_payee_cover ON transactions (payee_account) INCLUDE (status, amount);
-- original Q2 unchanged: each loop becomes Index Only Scan, Heap Fetches: 0
```

- H2: **0 / 0** for A, B1, B2.
- Discussion: B1 makes each loop fast but still visits 142,110 heap blocks; B2 needs no heap visits (index-only). A needs no new index (no write cost) and reads the table once.
- **B4 answer:** Option A is better when the panel covers *all* merchants or categories, when the table is write-heavy (no index to maintain), or when 47 MB of extra index is not acceptable.

---

## Q3 · Dormant merchants

**Baseline:** returns **0 rows**. `Index Scan using merchants_pkey`, `Filter: (NOT (ANY (merchant_account = (SubPlan 1).col1)))`, SubPlan `Materialize` with `loops=2000`, **temp read=136,487**. **~5.0 s.**

- Why 0 rows: 1,982 PENDING payments have `payee_account IS NULL`. `x NOT IN (…, NULL)` is never TRUE (it is NULL), so every merchant is filtered out.
- Why slow: 1M payee values do not fit in `work_mem` (4 MB), so there is no hashed sub-plan; the list is materialised to disk and re-scanned for each of the 2,000 merchants.

| Version | Plan | Pages | ms | Rows |
|---|---|---:|---:|---:|
| Baseline `NOT IN` | SubPlan Materialize, loops=2000, temp files | 13,007 + temp | 5,050 | **0 ❌** |
| `NOT EXISTS`, no index | Hash Right Anti Join | 12,626 | 148 | **50 ✅** |
| `NOT EXISTS` + payee index | Nested Loop Anti Join, Index Only Scan | 6,021 | 5–12 | 50 ✅ |
| ⚠️ Old `NOT IN` after payee index | Materialize via Index Only Scan, loops=2000 | — | **87,000** | 0 ❌ |

```sql
SELECT m.merchant_account, m.merchant_name, m.city
FROM merchants m
WHERE NOT EXISTS (SELECT 1 FROM transactions t
                  WHERE t.payee_account = m.merchant_account)
ORDER BY m.merchant_account;
```

- Correct answer: **50** merchants (merchant1951 … merchant2000).
- H2 against `lab05_q3_old`: **50 / 0**. That is expected: the old answer was wrong. Teams must *prove* it:
  - `SELECT count(*) FROM transactions WHERE payee_account IS NULL;` → 1,982
  - `NOT IN (SELECT payee_account FROM transactions WHERE payee_account IS NOT NULL)` → also 50 (correct but still the slow pattern).
- The 87-second row is why `lab05.sql` sets `statement_timeout = '60s'`. If a team hits the timeout, celebrate it as a finding.

---

## Q4 · Customer history, page 251

**Baseline:** Parallel Seq Scan (`Rows Removed by Filter: 329928` × 3) → Hash Join → Sort `rows=5020` → Limit 20. **12,894 pages, ~26 ms.**

| Version | Plan | Pages | ms |
|---|---|---:|---:|
| Baseline | Parallel Seq Scan + Sort | 12,894 | 26 |
| Composite index only (still `OFFSET 5000`) | Bitmap Heap Scan (7,017 blocks) + top-N Sort of 5,020 | 7,102 | 17–27 |
| **Index + keyset** | **Index Scan using idx_txn_payer_ts** + Nested Loop/Memoize | **72** | **0.07–0.1** |

```sql
CREATE INDEX idx_txn_payer_ts ON transactions (payer_account, txn_ts DESC, txn_id DESC);
-- keyset: see guide solution (\gset gives last_ts = 2026-02-16 02:16:30, last_id = 512128)
```

- The index alone barely helps: to skip 5,000 rows PostgreSQL must still produce them, and half of u42's 10,199 rows is too many for an ordered index walk, so it picks Bitmap + Sort.
- H2 (by `txn_id`): **0 / 0**. Page starts at txn 512087, ends at 511112.
- **B2 answer:** u42 has 10,216 payments; 17 are PENDING with `payee_account IS NULL`, so the inner `JOIN` drops them. Fix: `LEFT JOIN merchants` and `coalesce(m.merchant_name, '(pending)')`. Discuss: is hiding pending payments from the customer a bug? (Yes.)

---

## Best version: all fixes together

```sql
CREATE INDEX idx_txn_ts          ON transactions (txn_ts);                                  -- Q1
CREATE INDEX idx_txn_payee_cover ON transactions (payee_account) INCLUDE (status, amount);  -- Q2, Q3
CREATE INDEX idx_txn_payer_ts    ON transactions (payer_account, txn_ts DESC, txn_id DESC); -- Q4
```

- Q1 range rewrite · Q2 unchanged SQL (or Option A) · Q3 `NOT EXISTS` · Q4 keyset.
- Measured together: Q1 2.9 ms / 181 · Q2 22.8 ms / 1,854 · Q3 10.2 ms / 6,021 · Q4 0.1 ms / 72.
- Cheaper alternative: BRIN for Q1 (24 kB) and Option A for Q2 → only one 47 MB index (`idx_txn_payer_ts`) plus a payee index for Q3.

---

## How to run the debrief

1. **Scoreboard first.** Each team calls out its Q2 baseline and best pages. Write them on the board. Big numbers (3.9 M → 1,854) create energy.
2. **Q1, "the index that did nothing".** Ask a team that added the index first. Let them explain why the cast blocked it.
3. **Q2, the trap.** Ask: "Who used an inner JOIN?" Run the trap live and show the bottom-10 lists side by side. Ask: "Which list would the sales team use to call merchants?"
4. **Q3, wrong vs slow.** Ask: "Was Q3 slow or wrong?" (Both.) Show the `NULL` count. Highlight that the H2 check *disagreeing* was the evidence.
5. **Q4, OFFSET.** Show that the index alone left 7,102 pages; keyset brought it to 72.
6. **Cost.** Run helper H1: 115 MB of indexes on a 98 MB table. Ask: "Which index would you drop on a write-heavy system?"
7. **Close:** "Fast + same answer + known cost. That is what tuned means."

## Discussion prompts

- "Two fixes, each useless alone, together 70× fewer pages. What does that say about trying one thing and giving up?"
- "The fastest version of Q2 was wrong. How would you have noticed without H2?"
- "Q3's old answer was empty. Why is an empty result more dangerous than a slow one?"
- "Would you rather add a 47 MB index or rewrite the SQL? What do you need to know first?" (Write volume, other queries, maintenance.)
- "Which of these four bugs would you catch in code review just by reading the SQL?"

## Common trainer issues

- **Q2 baseline > 20 s** on slow laptops: fine. If it hits the 60 s timeout, use the reference numbers.
- **Teams re-run `NOT IN` after creating indexes** and wait 60 s: point to the ⚠️ in the hint.
- **H2 fails with "each EXCEPT query must have the same number of columns"**: the new query's column list must match the `_old` table exactly.
- **Keyset returns different rows**: the cursor must come from the same `JOIN` + `ORDER BY`; check `\echo :last_ts :last_id` → `2026-02-16 02:16:30 512128`.
- Plans differ? Check `reset.sql` was run, `statement_timeout` re-set, and `ANALYZE` after `CREATE INDEX` (the guide's fixes work without it; stats are already fresh).
