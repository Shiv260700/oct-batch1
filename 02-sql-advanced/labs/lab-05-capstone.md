# Lab 05 — Capstone: The Slow Dashboard

**SQL Performance Workshop · PostgreSQL 17 · File:** `sql/lab05.sql`

## The mission

- The **Operations Dashboard** has 4 panels. Each panel runs one SQL query.
- The head of operations complains:
  - *"The dashboard takes over 15 seconds to open."*
  - *"Sales says the **Dormant merchants** panel is empty. I don't believe it."*
- **Your team's job:** make every panel **fast** and **correct**, and **prove** both.

## You will use everything from Labs 01–04

| Skill | From |
|---|---|
| Read plans, count pages | Lab 01 |
| Choose the right index, keep columns "bare" | Lab 02 |
| Joins, `EXISTS` / `NOT EXISTS`, the `NOT IN` trap | Lab 03 |
| Group once, keyset pages, prove same answer | Lab 04 |

---

## Rules of the game

1. **Baseline first.** Run all 4 queries before changing anything.
2. **One change at a time.** Index *or* rewrite, then re-measure.
3. **Measure with `EXPLAIN (ANALYZE, BUFFERS)`.** Write down **ms and pages**.
4. **Prove the answer.** Run the "same answer?" check (helper H2) after every rewrite.
5. **An answer that changes is a bug**, *unless* you can prove the old answer was wrong.
6. **Write everything on the scorecard.** Your team presents it at the end.

## The fix loop

```text
 measure ──► ask the 5 questions ──► change ONE thing ──► measure again ──► same answer? ──► scorecard
    ▲                                                                                          │
    └──────────────────────────────────── not fast enough? ◄───────────────────────────────────┘
```

**The 5 questions** (from Lab 01)

1. Which node is most indented? Start there.
2. Seq Scan or index?
3. How many rows are thrown away (`Rows Removed by Filter`)?
4. Is `rows=` (estimate) close to the actual rows?
5. How many pages (`Buffers`)? How many `loops`?

---

## Part A — Run the baselines

```sql
\i sql/lab05.sql
```

- It runs `reset.sql`, sets a **60-second safety timeout**, runs all 4 panels, and saves today's answers into `lab05_q1_old` … `lab05_q4_old`.
- Total runtime: about 40 seconds. Q2 and Q3 are the slow ones.
- ✅ **Checkpoint:** the last lines show `q1 3 · q2 10 · q3 0 · q4 20` rows saved.
- Got `canceling statement due to statement timeout`? That is a finding. Write it down.

---

## Part B — The 4 panels

### Q1 · Daily summary

- **Business question:** payments, amount and failures per channel on **15 March 2026**.
- **Query:** `WHERE txn_ts::date = DATE '2026-03-15'`, grouped by channel.
- **Check your answer:** APP 6,677 · UPI_QR 2,810 · WEB 1,699 payments.

### Q2 · Grocery merchants to call

- **Business question:** the **10 GROCERY merchants with the lowest successful revenue**, including those with **₹0**.
- **Query:** a sub-query inside `SELECT` sums revenue for each merchant.
- **Watch:** the `loops=` number on the inner scan.

### Q3 · Dormant merchants

- **Business question:** merchants that have **never** received a payment.
- **Query:** `WHERE merchant_account NOT IN (SELECT payee_account FROM transactions)`.
- **Watch:** the number of rows returned. Is it believable?

### Q4 · Customer history, page 251

- **Business question:** customer `u42@bank`, page 251 (20 rows per page, newest first).
- **Query:** `ORDER BY txn_ts DESC, txn_id DESC OFFSET 5000 LIMIT 20`.
- **Watch:** how many rows are sorted and thrown away to show 20.

---

## Scorecard

Copy this table. Fill one row per change you try.

| Query | Version | What changed | Plan (top scan node) | Pages | ms | Rows | Same answer? |
|---|---|---|---|---:|---:|---:|---|
| Q1 | baseline | — | | | | 3 | — |
| Q1 | v2 | | | | | | |
| Q2 | baseline | — | | | | 10 | — |
| Q2 | v2 | | | | | | |
| Q3 | baseline | — | | | | | — |
| Q3 | v2 | | | | | | |
| Q4 | baseline | — | | | | 20 | — |
| Q4 | v2 | | | | | | |
| **All** | **total** | | | | | | |

- **Pages** = top-line `Buffers: shared hit + read`.
- **Index storage added:** run helper **H1** at the end and write the total here: ______ MB

---

## Hints (open one at a time)

### Q1 · Daily summary

<details><summary>Hint 1</summary>

- Look at the `Filter:` line. What is done to `txn_ts` before it is compared?
</details>

<details><summary>Hint 2</summary>

- Two problems, so two fixes. Try them **one at a time** and measure each:
  - a) There is no index on `txn_ts`.
  - b) `txn_ts::date` wraps the column, so a plain index on `txn_ts` can't be used.
- Does fix (a) alone help? Does fix (b) alone help?
</details>

<details><summary>Solution</summary>

- `CREATE INDEX idx_txn_ts ON transactions (txn_ts);`
- Replace the filter with a half-open range:
  `WHERE txn_ts >= TIMESTAMP '2026-03-15' AND txn_ts < TIMESTAMP '2026-03-16'`
- Both fixes are needed. Each one alone still reads every page.
</details>

### Q2 · Grocery merchants to call

<details><summary>Hint 1</summary>

- Find `SubPlan` in the plan. What is its `loops=` value? What runs inside it?
- `loops` × pages per loop = total pages.
</details>

<details><summary>Hint 2</summary>

- Option A: calculate revenue for **all** merchants **once** (`GROUP BY`), then join.
- Option B: keep the sub-query but give it an index, so each loop is cheap.
- ⚠️ Whatever you do, merchants with **₹0** revenue must still appear. Run the H2 check against `lab05_q2_old`.
</details>

<details><summary>Solution</summary>

- **Option A (rewrite):** `LEFT JOIN` to a grouped sub-query, with `coalesce(revenue, 0)`.
  - Must be a **LEFT** join. An inner `JOIN` silently drops the ₹0 merchants, the very ones sales wants to call.
- **Option B (index):** `CREATE INDEX idx_txn_payee_cover ON transactions (payee_account) INCLUDE (status, amount);`
  - Each loop becomes an **Index Only Scan**.
</details>

### Q3 · Dormant merchants

<details><summary>Hint 1</summary>

- Check: `SELECT count(*) FROM transactions WHERE payee_account IS NULL;`
- What does `x NOT IN (…, NULL)` return for any `x`?
</details>

<details><summary>Hint 2</summary>

- `NOT IN` + a `NULL` in the list = **no rows at all**. The panel is **wrong**, not just slow.
- Which Lab 03 pattern asks "does **no** matching row exist?"
</details>

<details><summary>Solution</summary>

- `WHERE NOT EXISTS (SELECT 1 FROM transactions t WHERE t.payee_account = m.merchant_account)`
- Correct answer: **50 merchants**. The H2 check shows 50 rows "only in new". That is expected, because the old answer was wrong.
- Faster still with an index on `payee_account` (the Q2 index works too).
- ⚠️ Do **not** re-run the old `NOT IN` after adding indexes. It can run for over a minute (the timeout will stop it).
</details>

### Q4 · Customer history, page 251

<details><summary>Hint 1</summary>

- `payer_account` is a foreign key. Does it have an index? (`\d transactions`)
- How many rows does the `Sort` / `Limit` handle to return 20?
</details>

<details><summary>Hint 2</summary>

- An index on `(payer_account, txn_ts DESC, txn_id DESC)` matches the filter **and** the order.
- Measure it. Is `OFFSET 5000` still a problem? Why?
- Lab 04: instead of "skip 5,000 rows", ask "rows **older than** the last row I showed".
</details>

<details><summary>Solution</summary>

- `CREATE INDEX idx_txn_payer_ts ON transactions (payer_account, txn_ts DESC, txn_id DESC);`
- Keyset page: get the last row of page 250, then continue from it:

```sql
SELECT t.txn_ts AS last_ts, t.txn_id AS last_id
FROM transactions t JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u42@bank'
ORDER BY t.txn_ts DESC, t.txn_id DESC
OFFSET 4999 LIMIT 1 \gset

SELECT t.txn_id, t.txn_ts, t.amount, t.status, m.merchant_name
FROM transactions t JOIN merchants m ON m.merchant_account = t.payee_account
WHERE t.payer_account = 'u42@bank'
  AND (t.txn_ts, t.txn_id) < (:'last_ts', :last_id)
ORDER BY t.txn_ts DESC, t.txn_id DESC
LIMIT 20;
```

- In the real app, `last_ts` / `last_id` come from the page already on screen. No `OFFSET` is needed.
</details>

---

## Bonus challenges (for fast teams)

- **B1.** Replace the Q1 B-tree with a **BRIN** index on `txn_ts`. Compare size (helper H1), pages and ms.
- **B2.** `u42@bank` has **10,216** payments, but Q4's join can only show **10,199**. Which 17 are hidden from the customer, and why? How would you show them?
- **B3.** Your indexes add how many MB? The table is 98 MB. Which index would you drop first, and what would get slower?
- **B4.** Q2 Option A reads ~12,600 pages; Option B reads ~1,850. When would Option A still be the better choice?

---

## Team debrief: present in this order

- **Before → after** for each panel: plan, pages, ms
- **One fix that did NOT help** on its own, and why
- **One answer that changed**, and how you proved which one is right
- **What it cost:** index storage added

## Common mistakes

- ❌ Changing two things at once → you can't tell which one helped
- ❌ Comparing ms only → compare **pages** too; ms change on every run
- ❌ "Faster" with fewer rows → check the H2 numbers, not your eyes
- ❌ Inner `JOIN` where the business wants zeros → use `LEFT JOIN` + `coalesce`
- ❌ Trusting `NOT IN` on a column that can be `NULL` → use `NOT EXISTS`
- ❌ Adding an index for every query → each one costs storage and slows writes

## Cleanup

```sql
DROP TABLE IF EXISTS lab05_q1_old, lab05_q2_old, lab05_q3_old, lab05_q4_old;
\i sql/reset.sql
```

**Next:** Lab 06 — Functions & Procedures
