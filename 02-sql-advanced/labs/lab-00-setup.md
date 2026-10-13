# Lab 00 — Setup and the Big Picture

**SQL Performance Workshop · PostgreSQL 17**

## You will be able to

- Start PostgreSQL and connect with `psql`
- Load the workshop data (1 million payments)
- Explain *where* rows live on disk, and what an index is
- Use the 6 `psql` commands needed in every lab

---

## Part 1 — The big picture (read before typing)

### How PostgreSQL is organised

| Level | Example | Think of it as |
|---|---|---|
| **Server** | PostgreSQL in Docker, port 5432 | The bank building |
| **Database** | `paylab` | One branch's records room |
| **Schema** | `public` | A cupboard in that room |
| **Table** | `transactions` | One register in the cupboard |
| **Role** | `labuser` | The staff ID card that opens doors |

### Where rows live: pages

- A table is stored as **pages** of **8 KB** each.
- Each page holds many rows (our `transactions` table: ~79 rows per page).
- 1,000,000 rows → **12,606 pages** → 98 MB.
- PostgreSQL always reads **whole pages**, never single rows.
- This storage area is called the **heap** (rows are in no special order).

### What an index is

- 📖 **Book analogy:** to find "UPI" in a 500-page book you don't read every page. You check the **index at the back** → it says "page 212" → you open only that page.
- A database index works the same way: a sorted list of values + where each row lives.
- No index → PostgreSQL must read **every page** (a *Sequential Scan*).

> **Remember:** Speed is mostly about **how many pages are read**. Every lab in this workshop is about reading fewer pages.

---

## Part 2 — Start PostgreSQL (choose ONE option)

### Option A — Docker Compose (recommended)

```bash
cd sql-advanced
docker compose up -d
docker logs advanced-sql-pg --tail 5      # look for: ready to accept connections
```

### Option B — `docker run`

```bash
cd sql-advanced
docker run -d --name advanced-sql-pg \
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe123 \
  -p 5432:5432 \
  -v advanced-sql-pgdata:/var/lib/postgresql/data \
  -v "$PWD":/workshop:ro \
  postgres:17
```

- Windows PowerShell: put it on one line and use `${PWD}` instead of `"$PWD"`.

### Option C — PostgreSQL already installed on your laptop

- Use it as is (version 15 or newer).
- Connect as your admin user: `psql -h localhost -U postgres -d postgres`

---

## Part 3 — Create your login and database

- Connect as the admin user:

```bash
psql -h localhost -U postgres -d postgres
# no psql on your laptop? use the one inside Docker:
docker exec -it advanced-sql-pg psql -U postgres -d postgres
```

- Run these **one at a time**:

```sql
CREATE ROLE labuser WITH LOGIN PASSWORD 'LabOnly_ChangeMe123';
CREATE DATABASE paylab OWNER labuser;
\q
```

- `CREATE DATABASE` cannot run inside `BEGIN ... COMMIT`.

---

## Part 4 — Connect as `labuser` and load the data

- **Always start `psql` from the `sql-advanced` folder**, because lab files use paths like `sql/lab01.sql`.

```bash
cd sql-advanced
psql -h localhost -U labuser -d paylab
# or, inside Docker (folder is mounted at /workshop):
docker exec -it -w /workshop advanced-sql-pg psql -U labuser -d paylab
```

- Load the workshop data:

```sql
\i sql/00_setup.sql
```

### ✅ Checkpoint — your output must show

| Check | Expected |
|---|---|
| accounts / merchants / transactions | **10,000 / 2,000 / 1,000,000** |
| first / last payment | **2026-01-01 00:00:00 / 2026-03-31 23:59:43** |
| SUCCESS / FAILED / PENDING | **941,023 / 48,998 / 9,979** |
| indexes | only 3 primary keys |

- Different numbers? Tell the trainer before moving on.

---

## Part 5 — The 6 `psql` commands you need

| Command | What it does |
|---|---|
| `\dt` | List tables |
| `\d transactions` | Show columns and indexes of a table |
| `\x auto` | Wide results shown vertically when needed |
| `\timing on` | Show how long each query took |
| `\i sql/lab01.sql` | Run a file |
| `\q` | Quit |

- Try them now: `\dt`, then `\d transactions`.

---

## Part 6 — Meet the data

```text
accounts (10,000)            transactions (1,000,000)              merchants (2,000)
─────────────────            ───────────────────────               ──────────────────
account_id  'u1@bank'  ◄──── payer_account                          merchant_account 'merchant1'
holder_name                  payee_account  ─────────────────────►  merchant_name
segment                      amount, status, channel, txn_ts         category
city, opened_on              txn_id (PK), upi_ref                     city
```

| Column | Values |
|---|---|
| `status` | SUCCESS (94%), FAILED (5%), PENDING (1%) |
| `channel` | APP (60%), UPI_QR (25%), WEB (15%) |
| `txn_ts` | 1 Jan 2026 → 31 Mar 2026 |
| `amount` | ₹1 → ₹49,021 (most payments are small) |

- Look at a few rows:

```sql
SELECT * FROM transactions LIMIT 5;
SELECT * FROM accounts WHERE account_id = 'u1000@bank';
SELECT * FROM merchants LIMIT 5;
```

- **Our story customer:** `u1000@bank`. You will meet this customer in every lab.

---

## Readiness checklist

- [ ] PostgreSQL is running (`docker ps` shows `advanced-sql-pg`)
- [ ] Connected as `labuser` to `paylab`
- [ ] `\i sql/00_setup.sql` checkpoint numbers match
- [ ] `\d transactions` shows 8 columns and 1 index (`transactions_pkey`)
- [ ] You can explain: page, heap, index

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `port 5432 already in use` | Another PostgreSQL is running. Use `-p 5433:5432` and connect with `-p 5433` |
| `container name already in use` | `docker start advanced-sql-pg` (it already exists) |
| `password authentication failed` | Check user/password. The admin password is set only the *first* time the volume is created |
| `sql/00_setup.sql: No such file` | You did not start `psql` from the `sql-advanced` folder. `\q`, `cd sql-advanced`, reconnect |
| `role "postgres" does not exist` (Mac Homebrew) | Your Mac username is the admin. Use `psql -d postgres` |
| `permission denied for schema public` | Database owner must be `labuser`: re-run Part 3 |

**Next:** Lab 01 — Reading an Execution Plan
