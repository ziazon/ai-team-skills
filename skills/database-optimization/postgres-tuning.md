# PostgreSQL tuning & scaling reference

General, engine-level PostgreSQL knowledge distilled from external write-ups (not
project-specific — measured project wins live in `LEARNINGS.md` beside this skill, when
your copy keeps one). Use as a checklist when diagnosing a slow Postgres, sizing config,
scaling reads/writes, or adding vector search. Numbers are starting points — always
`EXPLAIN (ANALYZE, BUFFERS)` and measure on real data before trusting them.

## Server / memory config (the first knobs)

Defaults ship tuned for a shared box, not a dedicated DB server — on a dedicated
instance they are almost always too small.

- `shared_buffers` — 25–40% of system RAM.
- `effective_cache_size` — 50–75% of system RAM (a planner hint, not an allocation;
  tells the planner how much OS+PG cache it can assume, so it favors index scans).
- `work_mem` — start 4–16MB **per sort/hash operation** (a single query can use several
  at once × connections, so don't set it huge globally; raise per-session for big
  analytical queries). Too low ⇒ sorts/hashes spill to disk.
- `maintenance_work_mem` — ~10% of RAM, cap ~2–4GB; speeds up VACUUM / CREATE INDEX /
  REINDEX.
- `effective_io_concurrency` — raise for SSD/NVMe (allows concurrent prefetch).
- `max_worker_processes` ≈ CPU cores; `max_parallel_workers_per_gather` ≈ 25–50% of
  cores (enables parallel scans/joins).

OS-level: mount the data dir `noatime`; `vm.swappiness` 1–10; SSD I/O scheduler
`noop`/`none` or `deadline`; disable transparent huge pages; put data, WAL, and indexes
on separate disks; SSD over HDD, RAID 10. Keep ≥20% free disk (>90% full is a danger
zone). Tools: `pgtune` for a config starting point.

## Diagnostics — find the problem before tuning

- **`pg_stat_statements`** — the single most useful extension; ranks queries by total
  time / calls / mean. Start every investigation here.
- **`EXPLAIN (ANALYZE, BUFFERS)`** — profile any query >~30s (or your SLO). Look for seq
  scans on big tables, nested-loop blowups, sorts spilling to disk, and row-count
  explosions from one-to-many joins. BUFFERS shows cache hit vs disk read.
- **Logging:** `log_min_duration_statement` (log slow queries), `log_lock_waits` (lock
  contention), `log_checkpoints`, `log_autovacuum_min_duration`. `pgBadger` to summarize
  the log.
- **Live activity:** `pg_stat_activity` (running queries, state, `query_start` age),
  `pg_stat_user_tables` (live/dead tuples, last (auto)vacuum/analyze), `pg_stat_io`,
  `pg_stat_user_indexes` (spot unused indexes to drop).

## Bloat & dead tuples (MVCC's tax)

Every UPDATE/DELETE leaves a dead tuple until VACUUM reclaims it; mass deletes/updates
without vacuum ⇒ table+index bloat ⇒ slower scans and wasted disk.

- **Detect:** dead-tuple ratio `n_dead_tup / NULLIF(n_live_tup,0)` from
  `pg_stat_user_tables`. **>30–40% = severe bloat.**

  ```sql
  SELECT relname, n_live_tup, n_dead_tup,
         round(n_dead_tup::numeric / NULLIF(n_live_tup,0) * 100, 1) AS dead_pct,
         last_vacuum, last_autovacuum, last_analyze
  FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
  ```

- **Fix (mild):** `VACUUM (ANALYZE) tbl`. **Fix (severe, VACUUM not keeping up):** rebuild
  — `CREATE TABLE new (LIKE old INCLUDING ALL)` → reload via `COPY` → `DROP old; ALTER
  TABLE new RENAME`. One real case freed ~1.5TB (~60% disk) and cut query time ~250%.
  `REINDEX` (or `pg_repack` for online) for index bloat.
- **Stale planner stats** (`last_analyze` NULL or months old) ⇒ bad plans. Run `ANALYZE`
  after any bulk load/delete.
- **Autovacuum tuning:** lower `autovacuum_vacuum_scale_factor` /
  `autovacuum_analyze_scale_factor` on large, frequently-updated tables (the default 20%
  means a billion-row table waits for 200M dead rows). Don't disable autovacuum globally;
  disabling per-table is a targeted-only escape hatch.

## Bulk operations

- **Load with `COPY`, not row-by-row INSERT** — ~3× faster than JDBC/batch inserts in
  practice (≈15min vs ≈40min for 250M rows), and atomic. Disable/defer constraints & FK
  checks during load, re-enable + `ANALYZE` after.
- **Batched deletes must vacuum between batches.** A multi-billion-row delete loop with no
  interleaved VACUUM guarantees catastrophic bloat (one case hit 44% dead tuples). Pattern:
  delete N (e.g. 100k) → COMMIT → `VACUUM (ANALYZE)` → repeat.
- **Slow `COUNT(*)` on huge tables:** use the planner estimate `n_live_tup` from
  `pg_stat_user_tables` (needs recent ANALYZE) or `MAX(id)`-based estimates when an exact
  count isn't required.
- **Prevent duplicate-row bloat at the schema:** add `UNIQUE` constraints + UPSERT
  (`ON CONFLICT`) rather than blind inserts; find existing dupes with
  `GROUP BY … HAVING COUNT(*) > 1`.

## Locks & contention

- **Find blockers:** join `pg_locks` ↔ `pg_stat_activity` on `pid`; check `mode`,
  `granted`, and `age(now(), query_start)`. `AccessShareLock` is permissive (coexists);
  `ShareUpdateExclusiveLock` blocks maintenance; `AccessExclusiveLock` (DDL) blocks
  everything.
- **Kill a stuck backend:** `pg_terminate_backend(pid)` (graceful: `pg_cancel_backend`).
- Schema changes (`ALTER TABLE`) take strong locks and queue behind long-running queries
  — see scaling rules below.

## Scaling reads & writes (OpenAI @ 800M users)

A single-primary Postgres **cannot scale writes** — there's one writer. The whole game is
protecting the primary's headroom and pushing everything else off it.

- **Offload reads to replicas.** OpenAI ran ~50 read replicas across regions; the primary
  serves writes + only the reads that truly need read-your-writes consistency. Route
  reporting/analytics/most app reads to replicas.
- **Ban long-running queries on the primary.** A query >1s persistently blocks autovacuum
  and queues schema changes behind it. Set `idle_in_transaction_session_timeout` and
  `statement_timeout`; move slow/analytical queries to replicas or optimize them. Idle
  open transactions are the silent killer (hold xmin → block vacuum → bloat).
- **Minimize load on the primary generally** — even reads — so it has burst headroom for
  write spikes (a spike that overloads the primary takes the whole app down).
- **Shard what you can.** Workloads that partition cleanly by key go to a horizontally
  sharded store; keep on single-primary Postgres only what's hard to shard, and migrate
  gradually.
- **Connection pooling is mandatory at scale.** Each PG connection is a process with real
  memory cost; put **PgBouncer** (transaction pooling) in front so thousands of app
  threads multiplex onto a bounded connection count. Don't raise `max_connections` to
  brute-force concurrency.

## Vector / GenAI search (pgvector)

For RAG / semantic search / recommendations, store embeddings in a `vector(d)` column and
add an ANN index. Two index types:

- **HNSW (default choice).** Best speed–recall tradeoff; no training step (build on an
  empty table); absorbs inserts without recall drift; query is O(log n). Costs more memory
  and builds slower. Params: `m` (connections/layer, default 16), `ef_construction`
  (build quality, default 64) — a good start is **`m=16, ef_construction=200`**; query-time
  `ef_search` (default 40) trades recall for latency (raise for accuracy, lower for speed).
- **IVFFlat.** Builds 12–42× faster, less memory — but needs training data present before
  indexing and recall drifts as data grows (rebuild needed). Param: `lists` (clusters);
  query-time `probes` (default 1 = terrible recall — set **10–50** depending on `lists`).
- **Rule of thumb:** default to **HNSW** unless build time/memory is the constraint and the
  dataset is fairly static. Match the index's distance op to your query (`<->` L2,
  `<=>` cosine, `<#>` inner product).
- **Hybrid search** (vector + relational `WHERE`): the relational predicate can fight the
  ANN index — verify the plan; partial indexes or pre-filtering by tenant/category help.
  Always benchmark **both** index types on your real data and queries; synthetic
  benchmarks lie.

## Operational-DB architecture for AI apps (Lakebase pattern)

Durable principles, vendor-neutral:

- **Separate compute from storage** so you can spin DBs up instantly, scale to zero, and
  size compute to bursty agent traffic independently of data size.
- **Branch the database like code** (copy-on-write) — cheap throwaway DBs forked from prod
  shape for testing agent behavior / parallel feature work without touching shared state.
- **Pair a write-optimized OLTP store with a read-optimized lakehouse**, unified by shared
  storage + metadata: operational ACID writes on the OLTP side, columnar/batch analytics
  on the lakehouse side, cheap flow between them.
- **Agent decision loops need low latency** (sub-100ms-class). Warehouses can't serve that
  — keep a dedicated operational layer in front of agents.

## Sources

- [Diagnosing & fixing critical PostgreSQL performance issues (dev.to / Pedro Gonçalves)](https://dev.to/pedrohgoncalves/diagnosing-and-fixing-critical-postgresql-performance-issues-a-deep-dive-3jj)
- [PostgreSQL tuning: 10 things to improve DB performance (Instaclustr)](https://www.instaclustr.com/education/postgresql/postgresql-tuning-10-things-you-can-do-to-improve-db-performance/)
- [Scaling PostgreSQL to power 800M ChatGPT users (OpenAI)](https://openai.com/index/scaling-postgresql/)
- [IVFFlat vs HNSW in pgvector (Tembo)](https://legacy.tembo.io/blog/vector-indexes-in-pgvector/)
- [A practical guide to building GenAI apps on a PostgreSQL-compatible DB (Yugabyte)](https://info.yugabyte.com/a-practical-guide-to-building-genai-apps-on-a-postgresql-compatible-database) — gated eBook; pgvector specifics filled from the Tembo write-up above
- [Lakebase for Dummies (Databricks)](https://www.databricks.com/resources/ebook/lakebase-for-dummies)
