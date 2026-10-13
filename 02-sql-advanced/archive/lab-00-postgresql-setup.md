# Lab 00 — PostgreSQL Environment Setup & Readiness

**Course:** Advanced SQL — PostgreSQL (3 days)  
**Level:** Preparatory lab  
**Goal:** Prepare a consistent PostgreSQL environment for execution plans, indexing, join optimization, query tuning, and PL/pgSQL labs.

## Learning outcomes

By the end of this lab, you will be able to:

- Start and connect to a PostgreSQL server.
- Create a dedicated training database and user.
- Run queries in `psql` or pgAdmin.
- Inspect server version and basic runtime settings.
- Execute `EXPLAIN (ANALYZE, BUFFERS)` safely on sample data.
- Confirm your environment is ready for subsequent labs.

## Prerequisites

- Docker Desktop or Docker Engine **recommended**, or a locally installed PostgreSQL server.
- A terminal (Windows PowerShell, macOS Terminal, or Linux shell).
- Optional: pgAdmin or another PostgreSQL SQL client.
- Available port **5432** (or choose another host port).

> **Convention:** Commands prefixed with `docker` run in your host terminal. SQL blocks run in `psql` or pgAdmin unless otherwise stated.

---

## Part A — Start PostgreSQL using Docker (recommended)

### Step 1. Confirm Docker is available

```bash
docker --version
docker info
```

If `docker info` fails, launch Docker Desktop or start the Docker daemon.

### Step 2. Create a persistent volume

```bash
docker volume create advanced-sql-pgdata
```

### Step 3. Start the training server

The lab uses PostgreSQL 17 so all participants run the same major version. Replace the example password for any environment exposed beyond your own laptop.

```bash
docker run -d \
  --name advanced-sql-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe123 \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -v advanced-sql-pgdata:/var/lib/postgresql/data \
  postgres:17
```

**Windows PowerShell (single line):**

```powershell
docker run -d --name advanced-sql-pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe123 -e POSTGRES_DB=postgres -p 5432:5432 -v advanced-sql-pgdata:/var/lib/postgresql/data postgres:17
```

> Port 5432 occupied? Replace `-p 5432:5432` with `-p 5433:5432`. Use port **5433** from host-side clients thereafter.

### Step 4. Check container health and logs

```bash
docker ps --filter name=advanced-sql-pg
docker logs advanced-sql-pg --tail 30
```

Look for `database system is ready to accept connections`.

### Step 5. Connect with psql inside the container

```bash
docker exec -it advanced-sql-pg psql -U postgres -d postgres
```

Inside `psql`:

```sql
SELECT version();
SELECT current_database(), current_user;
```

To leave `psql`:

```text
\q
```

---

## Part B — Alternative: existing local PostgreSQL installation

If PostgreSQL is already installed, **skip Part A**. Ensure the server is running and connect with a PostgreSQL superuser (often `postgres`).

```bash
psql -h localhost -p 5432 -U postgres -d postgres
```

On some macOS Homebrew installations, your OS username is the PostgreSQL administrator instead of `postgres`. Connect using that role and run the remaining setup SQL as an administrator.

Verify:

```sql
SHOW server_version;
SELECT current_user, inet_server_port();
```

> The subsequent SQL is shared across Docker and local-install paths.

---

## Part C — Create the training role and database

Run these commands as a PostgreSQL administrator while connected to the `postgres` database.

**Step 1 — Create a role.** Use a different password outside a disposable training laptop.

```sql
CREATE ROLE labuser WITH LOGIN PASSWORD 'LabOnly_ChangeMe123';
```

**Step 2 — Create the database.** Run this separately; `CREATE DATABASE` cannot run inside a transaction block.

```sql
CREATE DATABASE paylab OWNER labuser;
```

**Step 3 — Connect as the training user.** From the host, if `psql` is installed:

```bash
psql -h localhost -p 5432 -U labuser -d paylab
```

Or, with the Docker server:

```bash
docker exec -it advanced-sql-pg psql -U labuser -d paylab
```

> If you are inside `psql`, you can switch to the database using `\c paylab labuser` (you may be asked for the role password).

Confirm:

```sql
SELECT current_database() AS database_name,
       current_user AS connected_user,
       current_schema() AS schema_name;
```

Expected database: `paylab`; expected user: `labuser`.

---

## Part D — Optional pgAdmin connection

Register a server using:

| Property | Value |
|---|---|
| Name | Advanced SQL Lab |
| Hostname | localhost |
| Port | 5432 (or 5433 if remapped) |
| Maintenance database | paylab |
| Username | labuser |
| Password | The password set in Part C |

For pgAdmin running in **another container**, `localhost` points to the pgAdmin container, not to PostgreSQL. Use an appropriate shared Docker network and database-container hostname instead.

Open **Query Tool** against `paylab` and run:

```sql
SELECT now() AS server_time, current_database(), current_user;
```

---

## Part E — Create a small smoke-test dataset

This dataset is deliberately small. Larger, more realistic data is introduced in later labs so execution plans are meaningful.

```sql
DROP TABLE IF EXISTS lab00_orders;

CREATE TABLE lab00_orders (
    order_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    amount      NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    status      TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lab00_orders (customer_id, amount, status)
SELECT (g % 100) + 1,
       ((g % 500) + 1)::numeric,
       CASE WHEN g % 10 = 0 THEN 'FAILED' ELSE 'SUCCESS' END
FROM generate_series(1, 10000) AS g;

ANALYZE lab00_orders;

SELECT COUNT(*) AS total_orders,
       COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_orders,
       SUM(amount) AS total_amount
FROM lab00_orders;
```

**Expected:** 10,000 orders; 1,000 with `FAILED` status.

### Run your first execution plan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab00_orders
WHERE customer_id = 42;
```

Observe:

- **Scan type**: likely `Seq Scan` on this small, unindexed table.
- **Estimated rows** versus **actual rows**.
- **Execution Time**.
- **Buffers**: pages read from cache or storage.

`EXPLAIN ANALYZE` **actually executes** the statement. Exercise care with data-changing SQL (`UPDATE`, `DELETE`, `INSERT`) in later labs.

### Add an index and compare

```sql
CREATE INDEX idx_lab00_orders_customer_id
ON lab00_orders (customer_id);

ANALYZE lab00_orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab00_orders
WHERE customer_id = 42;
```

**Discussion:** Did PostgreSQL select `Index Scan` or `Bitmap Heap Scan`? Compare the estimated/actual row counts and buffers. An index does not guarantee a particular plan.

---

## Part F — Readiness checklist

- [ ] PostgreSQL server is running.
- [ ] PostgreSQL major version is known.
- [ ] `paylab` database exists.
- [ ] `labuser` can log in and create tables in `paylab`.
- [ ] pgAdmin or `psql` can execute SQL.
- [ ] `lab00_orders` contains 10,000 rows.
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` runs successfully.
- [ ] The difference between estimated and actual rows is visible in the plan.

### Submit these results to the trainer

```sql
SHOW server_version;
SELECT current_database(), current_user;
SELECT COUNT(*) AS rows_loaded FROM lab00_orders;
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'lab00_orders'
ORDER BY indexname;
```

Capture the results and one before/after execution-plan comparison.

---

## Part G — Common troubleshooting

### 1. Port 5432 is already in use

- Another PostgreSQL service or container may already use port 5432.
- In Part A map `-p 5433:5432`, then connect to **localhost:5433**.
- Container-internal `psql` continues using the default internal port 5432.

### 2. Container name already exists

```bash
docker ps -a --filter name=advanced-sql-pg
docker start advanced-sql-pg
```

Only if you intentionally want to replace that container:

```bash
docker rm -f advanced-sql-pg
```

The named volume persists unless explicitly deleted. Do **not** delete it if it contains work you need.

### 3. Password authentication failed

- Confirm the username, password, database, and host/port.
- `POSTGRES_PASSWORD` in `docker run` is applied **only on first initialization** of an empty database volume; restarting with a new value does not reset an existing role password.
- For role `labuser`, an administrator can use `ALTER ROLE labuser WITH PASSWORD 'new_password';`.

### 4. `role "postgres" does not exist` on a local Mac

- Homebrew setups may initialize the cluster with your macOS username as superuser.
- Connect with that role instead of assuming `postgres` exists.

### 5. `permission denied for schema public`

- Verify `paylab` is owned by `labuser`.
- As an administrator connected to `paylab`, run `GRANT USAGE, CREATE ON SCHEMA public TO labuser;` if permissions were changed from defaults.

### 6. Plan still chooses sequential scan after adding an index

- This is not necessarily an error. PostgreSQL decides based on table size, selectivity, statistics, and estimated cost.
- Inspect `ANALYZE`, estimated rows, and the number of matched rows.
- Later labs explore this in depth with larger tables.

---

## Cleanup (optional, after finishing the full course)

**Keep the environment for Labs 01 onward.** To stop the Docker server without deleting data:

```bash
docker stop advanced-sql-pg
```

To restart it:

```bash
docker start advanced-sql-pg
```

To remove only the smoke-test objects from the database:

```sql
DROP TABLE IF EXISTS lab00_orders;
```

> Do not remove the persistent volume until the entire course is complete and you no longer need the databases.

---

## Trainer notes

- Ask participants to explain the difference between **PostgreSQL server**, **database**, **role**, and **schema**.
- Clarify that **Docker is an environment choice**, not an SQL requirement.
- Demonstrate `EXPLAIN` (estimates only) versus `EXPLAIN ANALYZE` (executes and measures).
- Keep the plan comparison brief: subsequent modules cover planner internals, statistics, indexes, joins, and tuning in depth.
- **Next:** Lab 01 — Execution Plan Fundamentals.
