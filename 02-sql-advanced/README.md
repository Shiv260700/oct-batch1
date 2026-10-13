# SQL Performance Workshop (PostgreSQL)

Hands-on workshop for people who already know basic SQL (`SELECT`, `WHERE`, `JOIN`, `GROUP BY`).
One question runs through every lab:

> **Why is this query slow, and how do I make it fast without changing the answer?**

## Labs

| Lab | Topic | You learn to… |
|---|---|---|
| 00 | Setup & big picture | Run PostgreSQL, load the data; pages, heap, index |
| 01 | Reading an execution plan | Use `EXPLAIN (ANALYZE, BUFFERS)`; Seq / Index / Bitmap scans |
| 02 | Index design | Selectivity, composite order, date ranges, partial, covering, BRIN, index cost |
| 03 | Joins | Nested Loop / Hash / Merge, unindexed foreign keys, `EXISTS` / `NOT IN` trap |
| 04 | Rewriting queries | Group once, CTEs, top-N per group, keyset pagination, statistics, proving equivalence |
| 05 | Capstone: the slow dashboard | Diagnose and fix a real report, in teams |
| 06 | Functions & procedures | SQL & PL/pgSQL functions, volatility, plan caching, procedures with `COMMIT` |

## Folder layout

| Folder | Contents | Who |
|---|---|---|
| `labs/` | Lab guides (step by step, with real output) | Participants |
| `sql/` | `00_setup.sql`, `reset.sql`, `labNN.sql` | Participants |
| `slides/` | Slide decks: open `slides/index.html` in a browser | Trainer |
| `handouts/` | One-page cheat sheet (print it) | Everyone |
| `trainer/` | Answer keys and teaching tips | Trainer only |
| `archive/` | Previous version of the material | Reference |

## Quick start

```bash
cd sql-advanced
docker compose up -d
psql -h localhost -U postgres -d postgres     # then follow labs/lab-00-setup.md, Part 3
psql -h localhost -U labuser -d paylab
\i sql/00_setup.sql
```

- Start every lab with `\i sql/reset.sql`. It drops practice indexes; the data stays.
- Always start `psql` from the `sql-advanced` folder.

## The data (identical on every laptop)

| Table | Rows | Notes |
|---|---|---|
| `accounts` | 10,000 | `u1@bank` … `u10000@bank`; u42–u44 are very busy payers |
| `merchants` | 2,000 | 6 categories; `merchant1` is the busiest |
| `transactions` | 1,000,000 | 1 Jan – 31 Mar 2026, stored in time order |

- Story customer in every lab: **`u1000@bank`** (103 payments, 4 failed).

## Presenting the slides

| Key | Action |
|---|---|
| `→` `Space` `PageDown` | Next step / slide (works with clickers) |
| `←` `PageUp` | Back |
| `N` | Speaker notes |
| `O` | Overview of all slides |
| `F` | Fullscreen |
| `B` | Blank screen |
| `Ctrl/⌘ + P` | Save as PDF (one slide per page, all steps shown) |
