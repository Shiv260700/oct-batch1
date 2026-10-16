# Runbook: HikariCP connection pool exhausted

## Symptoms
- `java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms` in application.log.
- HTTP 500 with ~30 s latency on endpoints that use the database (often /api/orders).
- Pool stats show active=10, idle=0, waiting > 0.

## Likely causes
- A long-running query (reports, missing index) holds connections.
- Connection leak: code that does not close connections.

## Fix
1. Find and cancel the long query in PostgreSQL (`pg_stat_activity`, `pg_cancel_backend`).
2. Raise `maximumPoolSize` only if the database can take it.
3. Add a statement timeout for report queries; run reports on a read replica.
