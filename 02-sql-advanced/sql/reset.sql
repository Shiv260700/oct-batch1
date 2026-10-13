-- =====================================================================
-- SQL Performance Workshop — reset before every lab
-- =====================================================================
--     \i sql/reset.sql
--
-- Gives you a clean starting point without reloading the data:
--   * drops every index YOU created on accounts, merchants and transactions
--     (keeps the primary keys)
--   * drops extended statistics created in the labs
--   * resets session settings (work_mem, enable_*, parallel workers ...)
--   * removes leftovers of rolled-back test writes (keeps page counts exact)
--   * refreshes planner statistics
-- =====================================================================

\set ON_ERROR_STOP on

DO $$
DECLARE
    r record;
BEGIN
    -- Indexes that do not back a constraint (primary key / unique)
    FOR r IN
        SELECT i.indexrelid::regclass::text AS index_name
        FROM pg_index i
        JOIN pg_class c     ON c.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname IN ('accounts', 'merchants', 'transactions')
          AND NOT EXISTS (SELECT 1 FROM pg_constraint k
                          WHERE k.conindid = i.indexrelid
                            AND k.contype IN ('p', 'u'))
    LOOP
        EXECUTE format('DROP INDEX %s', r.index_name);
        RAISE NOTICE 'dropped index %', r.index_name;
    END LOOP;

    -- Extended statistics (CREATE STATISTICS ...)
    FOR r IN
        SELECT format('%I.%I', n.nspname, s.stxname) AS stat_name
        FROM pg_statistic_ext s
        JOIN pg_class c     ON c.oid = s.stxrelid
        JOIN pg_namespace n ON n.oid = s.stxnamespace
        WHERE c.relname IN ('accounts', 'merchants', 'transactions')
    LOOP
        EXECUTE 'DROP STATISTICS ' || r.stat_name;
        RAISE NOTICE 'dropped statistics %', r.stat_name;
    END LOOP;
END
$$;

RESET ALL;

-- Rolled-back test writes (UPDATE/INSERT ... ROLLBACK) leave dead rows that
-- make the table bigger. Rebuild it only when that happened, so page counts
-- always match the lab guides.
SELECT coalesce(sum(n_dead_tup), 0) > 0 AS needs_rebuild
FROM pg_stat_user_tables
WHERE relname IN ('accounts', 'merchants', 'transactions') \gset
\if :needs_rebuild
    \echo 'Rebuilding tables to remove leftovers from earlier test writes...'
    VACUUM FULL accounts;
    VACUUM FULL merchants;
    VACUUM FULL transactions;
\endif

VACUUM (ANALYZE) accounts;
VACUUM (ANALYZE) merchants;
VACUUM (ANALYZE) transactions;

\echo '=== Reset done. Remaining indexes (primary keys only): ==='
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('accounts', 'merchants', 'transactions')
ORDER BY tablename;
