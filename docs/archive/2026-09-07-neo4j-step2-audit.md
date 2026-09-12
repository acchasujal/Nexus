# Neo4j implementation record

## Step 2 — secure connection foundation (2026-09-07)

Verified before editing: branch `feat/neo4j-integration`, HEAD
`2ad00f68868dd679c955a8ba802ca7eb8af7d90c`, clean working tree. Read root
AGENTS.md, PROGRESS.md, current startup/configuration/repository/health code,
tests, manifests and Compose configuration again. The user's no-switch/no-commit
instructions take precedence over the branch workflow in AGENTS.md. No branch
switch, commit, push, deployment, history rewrite or external credential rotation.

### Implemented behavior and scope

- Added the official **neo4j==6.3.0** driver to both Python dependency manifests.
  This repository has no Python lockfile; the frontend package-lock.json is
  unrelated and unchanged. No new dependency manager or database framework.
- Added validated GRAPH_BACKEND (`memory`/`neo4j`), connection credentials and
  database selection, positive bounded timeouts in seconds, and an explicit
  required/degraded policy. Neo4j mode rejects missing credentials, invalid
  schemes/ports, embedded URI credentials, paths/query strings/fragments, and
  invalid/system database names. `NEO4J_PASSWORD` uses SecretStr and is excluded
  from settings serialization. Validation errors omit input values.
- `db/neo4j.py:Neo4jConnection` owns one reusable AsyncDriver/pool for each app
  lifespan (one app per worker process). There is no import-time Neo4j connection
  or per-request driver. Memory mode does not import/create/use the driver.
- Startup calls `verify_connectivity()` and a read-routed `RETURN 1 AS ok` in
  the explicitly selected database. The query checks authentication/database
  accessibility as well as transport. Queries use the configured server timeout;
  a client deadline of `2 * connection_timeout + query_timeout` bounds the probe.
  Connection acquisition also uses connection_timeout; automatic transaction
  retries are disabled for predictable health checks. Driver telemetry is disabled.
- Driver work is async and awaited. The existing PostgreSQL readiness probe is
  synchronous psycopg work offloaded through `run_in_threadpool`, with its existing
  15-second connect limit and a 2-second SQL statement timeout. This step does not
  rewrite the existing ingestion service's synchronous PostgreSQL mutation path.
- FastAPI wraps its original lifespan context, preserving framework/router
  startup/shutdown behavior. The pool closes on normal shutdown, connection
  startup failure, cancelled startup, and later startup-hook failure. Close
  exceptions produce a generic warning and `cleanup_failed`, not a false claim
  of successful cleanup. Driver exceptions/credentials are not interpolated into
  application logs or responses.
- PostgreSQL remains the record repository. Removed the embedded remote URL and
  default Neo4j password from application defaults and root .env.example.
  Unconfigured development starts explicitly in memory mode. Explicit PostgreSQL
  selection requires DATABASE_URL. Production requires JWT_SECRET_KEY; development
  can use a private ephemeral per-process signing key instead of a committed key.
  Auth verifier and templates no longer supply the old hardcoded signing default.
- Existing PostgreSQL error messages were sanitized at their source; transaction
  logic is unchanged. Legacy PostgreSQL-to-memory fallback in graph memory mode
  remains for compatibility but now makes readiness fail. Selecting Neo4j forbids
  that fallback if PostgreSQL initialization fails.
- Local Compose pins **neo4j:5.26.30-community**, binds published ports to loopback,
  removes APOC/unrestricted-procedure configuration, and requires private passwords
  from the environment. Its explicit `nexus-local` project and `neo4j_526_data`
  volume avoid automatically reusing/upgrading an older 5.20 volume. The backend
  no longer has a mandatory Compose dependency on Neo4j in memory mode.

**This is connectivity, not graph persistence.** No projection schema, graph
write/read implementation, synchronization revision or relationship codec has
been added. `GRAPH_BACKEND=neo4j` gates data operations with the existing HTTP 503
envelope and `projection=not_implemented`; it never runs them against the memory
or demo graph. Root metadata, login, health/readiness and system status remain
available. System status is explicitly degraded in Neo4j mode. The gate covers
all data routes, including ingestion/reviews/reset, so data cannot silently be
mutated through an unimplemented selected graph backend. Memory-mode successful
API contracts and NetworkX algorithms remain unchanged.

### Liveness, readiness and failure policy

`/health` and `/api/v1/health` remain process-liveness probes, without database
queries. Existing duplicate core/system health registrations are preserved.
`/ready` and `/api/v1/ready` actively probe required storage and Neo4j; they expose
actual storage, storage_available, dependencies_ready, graph connection state,
failure policy, operational flag and projection status. Neo4j readiness counts
are zero rather than presenting the repository's memory counts as a Neo4j graph.

| Mode/policy | Startup | Readiness in this step | Data operations |
| --- | --- | --- | --- |
| memory, storage available | No Neo4j work | 200 ready; graph connection disabled | Existing behavior |
| neo4j + required, connection fails | Aborts; closes driver | No ready application from that startup | Unavailable |
| neo4j + required, connection succeeds | Starts; pool reused | **503 not_ready**, dependencies_ready=true, projection not_implemented | 503; no memory fallback |
| neo4j + required, connection later fails | Process remains alive | 503; dependencies_ready=false | 503 |
| neo4j + degraded, connection succeeds or fails | Starts with connection state visible | **200 degraded** if required storage is available; operational=false | 503 until projection exists |
| Any mode, required storage unavailable/fallback | Existing memory-mode fallback only, or startup failure in Neo4j mode | 503 if application remains running | Not a ready service |

Degraded is an explicit opt-in to a diagnostics-only Neo4j foundation, not
permission to substitute graph data. Probes can recover a degraded connection
using the same pool. Failure to construct a driver (for example a missing package)
requires fixing the installation and restarting. Optional graph availability
does not make PostgreSQL optional. A successful connection will only make a
required Neo4j application operational after the future projection/read step.

### Configuration and local setup

Selected-version compatibility was checked against the official
[driver 6.3.0 release](https://github.com/neo4j/neo4j-python-driver/releases/tag/6.3.0),
[Python/server compatibility matrix](https://neo4j.com/docs/python-manual/current/install/),
[async driver API](https://neo4j.com/docs/api/python-driver/current/async_api.html),
and [Neo4j 5.26.30 release notes](https://neo4j.com/release-notes/database/neo4j-5-26-30/).
Driver 6.x supports Neo4j 5.x and Python >=3.10, encompassing this project's
Python >=3.11 requirement. The actual 6.3.0/5.26.30 pair and the implemented
Cypher 5 connectivity queries passed the isolated smoke test; projection Cypher
does not yet exist and is not claimed as verified.

| Environment variable | Default / validation |
| --- | --- |
| GRAPH_BACKEND | memory; accepts only memory or neo4j |
| NEO4J_URI | Empty; required in Neo4j mode; bolt/neo4j schemes including +s/+ssc |
| NEO4J_USER | Empty; nonblank in Neo4j mode |
| NEO4J_PASSWORD | Empty private SecretStr; nonblank in Neo4j mode |
| NEO4J_DATABASE | neo4j; user database name, 3–63 letters/digits/dots/hyphens |
| NEO4J_CONNECTION_TIMEOUT | 5 seconds; >0 and <=120 |
| NEO4J_QUERY_TIMEOUT | 10 seconds; >0 and <=300 |
| NEO4J_FAILURE_POLICY | required; accepts required or degraded |
| NEXUS_REPOSITORY / DATABASE_URL | memory / empty by default; explicit postgres selection requires a URL |
| JWT_SECRET_KEY | Private configured value; otherwise ephemeral in development and rejected in production |

From the repository root, install the existing backend requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit the local ignored .env privately. For Compose, fill POSTGRES_PASSWORD and
NEO4J_PASSWORD with distinct random values; use a URL-safe PostgreSQL password
for the Compose URL interpolation. Never print the resolved Compose configuration.
Do not overwrite an existing .env, copy credentials from history, or reuse a
shared database. Retain the private local Neo4j password across restarts: changing
NEO4J_AUTH does not reset a password in an already initialized volume.

To start only the dedicated local development databases (not executed by this
step; the smoke test below uses a separate container):

```powershell
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d postgres neo4j
```

Set GRAPH_BACKEND=neo4j in .env and start the local backend when inspecting the
connection foundation:

```powershell
docker compose --env-file .env up -d backend
```

Required mode's /ready=503 after a successful connection is expected in Step 2:
read `dependencies_ready` and `graph.projection`. Use degraded only when you
explicitly want the diagnostics process to remain ready while graph operations
are unavailable. Keep GRAPH_BACKEND=memory to use the current synthetic demo.
No production/deployment command is provided. Do not attach the old Neo4j volume
without a separately reviewed upgrade, and do not use `down -v` on team resources.

### Tests and the isolated real connection smoke test

`tests/conftest.py` now sets safe memory/database/AI/auth configuration **before
collection imports the module-level application**, and disables .env settings
loading for tests. It does not alter local .env files. Integration opt-in is a
separate variable; unit tests never pick up a deployment URL or password.

```powershell
New-Item -ItemType Directory -Path .test-tmp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -o addopts= --tb=short --basetemp=.test-tmp/neo4j-full
$env:NEXUS_RUN_NEO4J_SMOKE = '1'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_neo4j_connection.py -q -o addopts= --tb=short
Remove-Item Env:NEXUS_RUN_NEO4J_SMOKE
```

The smoke test refuses remote Docker contexts: it requires a Unix socket or
Windows named-pipe endpoint and pins each Docker operation to that context.
It accepts no existing database URI. It creates a unique labeled container and
volume, allocates an ephemeral loopback Bolt port, supplies a random private
password through process environment, and executes only connectivity/version
queries. It verifies server version/edition, valid authentication, rejection of
an invalid password and missing database, and driver closure. Cleanup checks
exact ownership labels before removing only its own container and volume.
It does not use root Compose, a production database, shared records, APOC or GDS.

### Commands actually executed and results

Final environment: Python 3.13.1 in the existing project .venv, Neo4j driver
6.3.0, FastAPI 0.141.1, Starlette 1.6.0, pytest 8.4.2, NetworkX 3.6.1,
psycopg 3.3.5 and Ruff 0.16.4. Step 1 used the system interpreter; these versions
are reported explicitly rather than claiming identical environments.

| Executed command/check | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pip install neo4j==6.3.0` | PASSED after approved network escalation; installed driver and pytz in .venv. |
| `.venv/Scripts/python.exe -m pip install -r backend/requirements.txt` | PASSED; completed the existing partial .venv (reportlab and other declared dependencies were missing). |
| Focused pytest: `tests/test_neo4j_foundation.py tests/test_system_health.py -q -o addopts= --tb=short --basetemp=.test-tmp/neo4j-foundation` | PASSED: **34 tests**, 10.90 s. Later small cleanup-status/config changes are also covered by the final full run. |
| Full pytest: `-q -o addopts= --tb=short --basetemp=.test-tmp/neo4j-full` | PASSED: **699 passed, 2 skipped, 3 warnings**, 176.96 s. Skips are the opt-in smoke test and the previously identified empty-evidence fixture. |
| Opt-in pytest: `tests/integration/test_neo4j_connection.py -q -o addopts= --tb=short --basetemp=.test-tmp/neo4j-smoke` | PASSED against real local Neo4j: initially 15.46 s; final run after local-context/cleanup hardening **1 passed, 18.52 s**. |
| `.venv/Scripts/python.exe scripts/evaluate_ground_truth.py` | PASSED: TP=2, FP=0, FN=0; 100% precision/recall/F1. |
| `.venv/Scripts/python.exe -m ruff check backend/ shared/ tests/ --output-format concise` | PASSED: all checks passed. |
| `docker desktop start --detach`; `docker version --format '{{.Server.Version}}'` | PASSED with approved escalation; local Docker Desktop started, engine 29.2.1. |
| `docker pull neo4j:5.26.30-community` | PASSED; image digest `sha256:037cf5756f0135cbfd66b739b6df7c7c4bb100f9ce11602f6f9538e17e02c74d`. |
| `docker compose --env-file .env.example config --quiet` with ephemeral private process variables | PASSED; resolved configuration not printed and no development stack started. |
| Docker container/volume listing filtered by `io.nexus.connection-smoke` | PASSED after the first smoke run: no matching resources remained; final smoke also completed ownership-checked cleanup. |
| Value-suppressed scan of tracked source/template working files | PASSED: no non-placeholder remote PostgreSQL URI found; only the existing redacted documentation example matched. |
| `git diff --check` | PASSED; only Git's LF/CRLF normalization notices. |
| Frontend tests/build/lint | NOT RUN in Step 2; frontend sources and contracts unchanged. Step 1's frontend lint failures remain baseline debt. |
| PostgreSQL durability/projection/migration integration tests | NOT RUN; outside this connection-foundation step. |

Failed attempts, not final pass claims: the sandbox first blocked PyPI and Docker
access; approved retries succeeded. Initial focused tests could not collect due
to missing reportlab. After installing declared requirements, 8 tests exposed
removed APIRouter startup/shutdown methods in this .venv; replaced those calls by
wrapping the original lifespan and reran successfully. The first full run had
683 passes and 16 fixture setup errors because `.test-tmp` did not exist; created
the parent and the complete retry passed. No application failures remain in the
final run. Existing short-HMAC fixture warnings and the .venv Starlette/httpx
deprecation warning are not suppressed or described as test failures.

Logs are local `%TEMP%/nexus_step2_{dependencies,foundation,full_retry,smoke_final}.log`.
The Docker Desktop process remains running and the downloaded image is cached;
the smoke database is removed. No development stack was launched.

### File responsibilities, troubleshooting and remaining work

| Created/modified file | Responsibility |
| --- | --- |
| `backend/app/db/neo4j.py` (new) | Async driver ownership, connectivity/query probes, safe errors and cleanup |
| `backend/app/config.py`, `.env.example` | Validated selection/credentials/timeouts/policy and safe development defaults |
| `backend/app/auth/verifier.py`, `configs/.env.example` | Remove committed signing-key defaults; use the configured or ephemeral development key |
| `backend/app/main.py` | Wrap existing lifecycle, share connection, prevent PostgreSQL fallback in Neo4j mode |
| `backend/app/api/dependencies.py` | Explicit temporary Neo4j data-operation gate; no memory substitution |
| `backend/app/api/system_routes.py` | Required-dependency readiness, async-safe PostgreSQL probe, honest graph capability/status |
| `backend/app/db/postgres.py` | Sanitize existing database-error logs only; persistence semantics unchanged |
| `pyproject.toml`, `backend/requirements.txt` | Matching official driver pin |
| `docker-compose.yml` | Pinned local-only Neo4j with persistent storage and no extra plugins |
| `tests/conftest.py`, `pytest.ini` | Safe collection-time configuration and integration marker |
| `tests/test_neo4j_foundation.py` (new) | Configuration, lifecycle, policy, failures, cancellation, redaction and no-fallback tests |
| `tests/integration/test_neo4j_connection.py` (new) | Opt-in, self-owned real local Neo4j smoke test |
| `docs/NEO4J_IMPLEMENTATION.md` | Actual behavior, commands/results, setup and limitations |

Troubleshooting: if Docker's named pipe/socket is missing, start Docker Desktop
and check engine availability. A missing driver requires installing requirements
with the same interpreter that runs Uvicorn. For rejected configuration, check
variable names, positive timeouts and separate credentials from the URI. For
connection failures, privately verify the Bolt address, TLS scheme, password and
database; a successful HTTP browser probe alone is insufficient. A reused volume
keeps its initialized authentication; do not delete shared data to resolve an
auth error. Driver exceptions and resolved settings are intentionally withheld
from public diagnostics. After changing credentials/configuration, restart the
application; environment changes do not mutate an existing pool.

**Owner action remains required:** rotate the previously exposed remote PostgreSQL
credential and any deployed secret that reused committed defaults. This step
removed current defaults/templates, not historical exposure, and did not attempt
rotation. Development JWTs without an explicit key expire across process restarts;
multiple workers need a shared private configured key.

Projection writes/reads, lossless relationship metadata, synchronization/lag
revisions, reliable PostgreSQL transaction boundaries, durable review/audit
restart parity, and broader case authorization remain future work from Step 1.
There are no new guilt scores or graph-based claims of criminal involvement.

Suggested commit message:
`feat(neo4j): add secure configuration and managed driver lifecycle`

---

The following Step 1 and Step 0 sections are historical audit records. Step 2
above supersedes their missing-connection/configuration findings only.

## Step 1 — architecture audit and test baseline (2026-09-07)

**Scope:** read-only runtime audit; documentation is the only tracked change.
Neo4j persistence, reads, synchronization, and lifecycle management are not
implemented. Proposed interfaces below are proposals, not shipped capabilities.

### Checkout and applicable instructions

- Workspace: `C:/Users/vikram/OneDrive/Desktop/Nexus`.
- Branch: `feat/neo4j-integration`.
- HEAD: `9329187c2b52608e87394313ed9aa4d65c1b2062`
  (`docs: record verified Neo4j integration baseline`). This differs from step 0.
- Initial `git status --short`: empty. The existing step-0 document is committed
  in this checkout; this audit did not create that commit.
- `git merge-base HEAD origin/main`: `952bcb95fefb306f7281815785ed39f48ef476ec`.
  This is a local reference comparison, not proof of the team's active branch
  or remote freshness. No fetch, branch switch, reset, commit, push, or deployment.
- Root `AGENTS.md` is the only instruction file found by repository search.
  It prioritizes implemented code and tests over product/progress documents,
  requires synthetic data, cited relationships and deterministic graph analysis,
  and forbids predictive guilt scoring. `PROGRESS.md` was read; its historical
  test counts are superseded by the measurements below for this checkout.
- The user's explicit instruction to preserve the branch and make no runtime
  changes overrides AGENTS.md's branch-switch/create workflow. No PR is being
  opened; PROGRESS.md and runtime files are unchanged.

### Verified architecture and complete upload-to-graph path

1. **Frontend upload:** `frontend/src/components/CsvIngestionPanel.tsx` calls
   `useIngestFiles()` in `hooks/useIngestion.ts`. That hook calls
   `lib/apiClient.ts:nexusIngest`, posting multipart FIR/CDR/bank/intelligence
   files to `/api/v1/nexus/ingest`. The separate `apiClient.ingestFiles` method
   posts to `/api/v1/ingest`; the hook's comment currently names that older path.
2. **HTTP validation:** `api/nexus_routes.py:956` and `api/core_routes.py:600`
   check CSV filenames, emptiness, and a 5 MiB per-file limit, then construct
   `UploadedSource` values. Nexus upload normalizes filenames to known source
   filenames; core upload retains uploaded names. Both resolve the app-level
   `IngestionService` through `api/dependencies.py`. The core route requires
   SP/SUPERVISOR; the Nexus route does not repeat that role check.
3. **Orchestration:** `services/ingestion_service.py:ingest_files` enforces
   one-to-four files, takes a process-local `asyncio.Lock`, records INGESTION_STARTED,
   and calls the shared `CsvIngestionPipeline.ingest_batch`.
4. **Parsing/normalization:** `db/ingestion/csv_reader.py`, `normalization.py`,
   `quality.py`, and `parsers/{fir,cdr,bank,intelligence}.py` read bytes, validate
   headers and rows, normalize fields, record issues/duplicates/conflicts, and
   produce `ParsedSourceBundle` records. Source records retain locators and
   hashes; `identifiers.py` supplies deterministic identifiers.
5. **Entity resolution:** `pipeline.py:_extract_claims/_resolve_parsed` creates
   `IdentityClaim`s, deterministically orders them by corroborating fields,
   and invokes `resolution/matcher.py:decide_candidates` using the shared
   in-process `IdentityRegistry`. Auto-link-allowed matches select canonical IDs;
   ambiguous matches produce human review candidates. NOT_MATCHED decisions are
   excluded from the review queue. The registry is updated during parsing,
   before repository validation/commit, and is neither restored from PostgreSQL
   at startup nor reconciled by the merge endpoint.
6. **Mapping/bundle validation:** `mappers/{fir,cdr,bank,intelligence}.py`
   converts canonical mappings and parsed sources into typed nodes and directed
   `GraphEdge`s. `pipeline.py:_combine/_finalize` deduplicates nodes/edges by ID,
   validates references, attaches issues/reviews/counts, and returns the
   `IngestionBundle` defined in `contracts.py`. It also builds its own analytical
   store with `graph_adapter.py:build_m1_graph_store`. That intermediate store
   is not the application repository's persisted graph.
7. **Persistence:** the service rejects fatal header/text errors, computes
   duplicate/conflict counts, calls `repo.apply_bundle(bundle)`, separately
   stores review candidates, refreshes the shared graph repository through
   `repo.to_graph_store()`, records INGESTION_COMPLETED, and maps response counts.
   Both operational repositories revalidate bundle references in `apply_bundle`.
   These calls do not form one atomic transaction; see transaction findings.
8. **Graph reads and API serialization:** there are multiple paths, not one
   universal GraphStore gateway:
   - `main.py:126` supplies `GraphRepository(repository.to_graph_store())` to
     `/api/v1/graph/*` and its GraphService/HotspotService/OffenderService.
   - Core case/entity/evidence/algorithm services call the operational
     repository's `to_graph_store()` as needed. Case routes serialize through
     `get_case_network`; entity routes through `EntityService`.
   - `/nexus/network` reads `repo.nodes`/`repo.edges` directly and appends static
     BEFORE/AFTER demo records. `/nexus/batches/{batch_id}/network` reads
     `repo.batches` directly. Source/evidence lookup still depends on authoritative
     source records and raw edge dictionaries. Pathfinder combines repository
     graph data with snapshot/demo paths. Merely replacing GraphRepository
     would not route all graph reads to Neo4j.
9. **Frontend rendering:** `graph_ready` triggers React Query invalidation in
   `useIngestion.ts`; the panel links to `/network?batch_id=...` and the review
   workspace. `hooks/useNexus.ts` fetches batch/global/entity/case networks.
   `pages/NetworkExplorer.tsx` selects the active graph and renders
   `components/nexus/GlobalNetworkCanvas.tsx` → `D3NetworkGraph.tsx`.
   CaseDetail's `NetworkAnalysisPanel.tsx` uses `hooks/useCaseNetwork.ts` and also
   renders D3. React Flow remains a dependency/chunk, but these current graph
   surfaces use D3; the older progress description is not an implementation map.
   Existing response types are in `shared/contracts/api.py` and `api.ts`.

### Storage, transactions, and mutation integration points

| Area | Verified implementation and limitation |
| --- | --- |
| Operational repositories | `db/in_memory.py:InMemoryBackendRepository` and `db/postgres.py:PostgresBackendRepository`; they expose dictionaries plus domain methods. The ABCs in `db/repositories/interfaces.py` are not the concrete runtime wiring. |
| Memory persistence | Synthetic artifact plus optional JSON state. `_save_state()` saves audit/review state, not a complete durable ingested graph. |
| PostgreSQL startup | Constructor executes `db/schema.sql`, loads nodes/edges/sources/audits/reviews, optionally seeds an empty database from an artifact, then rebuilds indexes. No database was contacted in this audit. |
| Actual migrations | Runtime executes `db/schema.sql` with psycopg. `db/migrations/schema.py` contains a separate legacy DDL catalog; its CLI prints status/verification and does not apply migrations. Its descriptive header overstates implemented migration machinery. Do not build a new runner on that assumption. |
| Bundle commit | `postgres.py:348–516` first mutates dictionaries/indexes, then writes nodes, edges, source records, and a batch summary in one SQL transaction. Database exceptions are logged and swallowed; successful counts still return. Database rollback does not undo the prior memory mutations. |
| Reviews | `store_review_candidates` uses a separate SQL transaction after bundle persistence. `update_candidate_status` changes memory before a separate SQL commit and swallows errors. Stored/reloaded review columns omit several contract fields, including supporting references/reasons/conflicts. |
| Human decisions | `nexus_routes.py:1163–1239` maps CONFIRM/REJECT/DEFER; sets status, then writes decided_by/decided_at directly into the dictionary. CONFIRM calls `merge_nodes`, refreshes the graph, then audits separately. Those decision metadata fields have no matching SQL write here. Static demo candidates use `_demo_state` instead. |
| Merge/update/delete | Both `merge_nodes` implementations combine properties (canonical wins), redirect source/target IDs, preserve existing edge IDs, remove the incoming node, and rebuild indexes. PostgreSQL performs canonical UPDATE, endpoint UPDATEs, and incoming DELETE in its own transaction after changing memory; errors are swallowed. No general entity PATCH/PUT/DELETE route was found. Bundle upserts and merges are the operational entity-update paths. |
| Reset | `/nexus/demo/reset` calls `repo.clear()` and refreshes GraphRepository. PostgreSQL clear executes TRUNCATE CASCADE on application tables and reseeds. This route has no dedicated local-database or explicit admin guard in the inspected handler. It was never called against a database in this audit. |
| Audit | `AuditService.record` appends memory, performs an optional direct SQL write in a separate connection, and suppresses errors. SQL persists only part of the generated payload; top-level integrity/previous hashes and request/case metadata do not round-trip as the original event. `PostgresBackendRepository.record_audit` is another write path. Neither belongs in Neo4j as the authoritative audit store. |
| Restart consistency | PostgreSQL loads source hashes as `hash`, while ingestion duplicate/conflict lookup expects `content_hash`. `_load_from_postgres` does not reconstruct batch graph membership. Review payload, source context, merged badges, and identity-registry state are incomplete across restart. |

### Graph structures and metadata preservation

`core/graph/algorithms/utils.py` defines NodeRecord, directed AdjEdge, and GraphStore
with outgoing/incoming adjacency and a relationship-type index. Existing
NetworkX routines and deterministic traversals operate on these structures.
The generic builder deduplicates by edge ID when available, otherwise by
type/source/target; its docstring's unconditional deduplication description is
not the full implemented behavior.

Both operational `to_graph_store()` implementations currently copy only edge
weight and provenance into AdjEdge properties. They omit stable edge ID,
source_record_id, derivation_class, temporal bounds, confidence, and arbitrary
domain properties. `db/ingestion/graph_adapter.py:_edge_properties` preserves
more of these fields and is the reuse point for a unified codec, but it too
must be extended for all GraphEdge fields. In particular, `GraphEdge` has
top-level `storage_mode`, `weight`, and `created_at`; bundle persistence currently
does not faithfully serialize them all. PostgreSQL insertion derives weight
from `edge.properties`, not `edge.weight`. Existing missing metadata cannot be
recovered by copying the lossy GraphStore; retain it at authoritative ingestion
and backfill only from verified synthetic source records, never invented values.

`validate_graph_references` checks endpoints and FACT source-record references
within the bundle. PostgreSQL has endpoint foreign keys, but `source_record_id`
is not a source-record foreign key in the current schema. DERIVED/HYPOTHESIS
lineage needs explicit coverage beyond that FACT-only check.

The global Nexus serializer currently forces `derivation_class="FACT"` and uses
the current time for `recorded_at`. Batch serialization preserves derivation
but synthesizes a timestamp when absent. Fallback edge IDs based only on endpoints
can collide for parallel relationships. These are existing defects to address
at the integration boundary, not behavior to preserve as evidence semantics.

### Every `to_graph_store()` location at audited HEAD

Line numbers refer to the audited commit; repeated line numbers below are
individual calls. Definitions are listed separately.

| File | Lines |
| --- | --- |
| `backend/app/db/in_memory.py` | definition 304; internal call 458 |
| `backend/app/db/postgres.py` | definition 643; internal call 789 |
| `backend/app/main.py` | 126 |
| `backend/app/api/dependencies.py` | 171, 181 |
| `backend/app/api/core_routes.py` | 220, 259, 286, 311, 350, 372 |
| `backend/app/api/nexus_routes.py` | 1095, 1216, 1443, 1799 |
| `backend/app/services/ingestion_service.py` | 101 |
| `backend/app/services/entity_service.py` | 64, 152, 219 |
| `backend/app/services/evidence_service.py` | 120, 159, 194, 230, 271 |
| `backend/app/services/copilot_service.py` | 117, 444 |
| `backend/app/services/lead_service.py` | 96 |
| `backend/app/ai/context_builder.py` | 78 |
| `backend/app/ai/tools.py` | 394, 544, 797, 839, 880, 924 |
| `scripts/benchmark_nexus.py` | 37 |
| `scripts/evaluate_ground_truth.py` | 31 |
| `tests/services/test_ingestion_service.py` | 19 |
| `tests/ingestion/test_repository_integration.py` | 79 |
| `tests/test_copilot_intent.py` | 93 |
| `tests/test_evidence_api.py` | 62, 285 |
| `tests/test_entity_api.py` | 55, 139, 207, 230, 248, 265 |
| `tests/test_hotspot_offender_intelligence.py` | 24 |
| `tests/test_nexus_entity_resolution.py` | 29 |

### Verification of the earlier hypotheses

| Hypothesis | Finding |
| --- | --- |
| Missing Neo4j driver | CONFIRMED: absent from both dependency manifests and installed Python distributions. Configuration and Docker declarations do not provide a Python driver. |
| Database-loading stub | CONFIRMED: `GraphRepository.load_from_db` stores a session and returns the injected store. `refresh` replaces the store with an empty one, then calls that stub if a session exists. No external runtime invocation of these load/refresh methods was found; actual startup injects a store. |
| Incorrectly nested methods | CONFIRMED by source and AST: `_add_node` (140) and `_add_edge` (148) are nested inside `_match_filter`, after its unconditional return, rather than GraphRepository methods. They are unreachable helper definitions. |
| Inconsistent construction | PARTIALLY CONFIRMED: `create_app` constructs one operational repository and shared GraphRepository; dependency factories at `api/dependencies.py:172,182` and `lead_service.py:144` construct additional GraphRepository wrappers. They wrap the injected operational repository's store rather than constructing additional PostgreSQL backends. Script entry points separately construct memory repositories. The zero-argument GraphRepository example in graph_routes is a docstring, not an executed call. |

### Authentication, case access, lifecycle, health, and test coverage

- `auth/principal.py` supplies canonical officer identity; `auth/verifier.py`
  verifies signed JWTs but also accepts base64 session payloads and development
  role headers. Base64 parsing precedes the production invalid-token rejection;
  missing-token header-role handling is not gated by production mode.
  `core_routes.py:/auth/login` signs the requested identity/role without a
  credential-validation step. These are existing demo/authentication limitations.
- `auth/policy.py:EvidenceAuthorizationPolicy` applies role/case/station/district
  rules for protected evidence routes. `tests/test_evidence_rbac.py` and
  `tests/test_auth_canonical_identity.py` exercise parts of this policy/identity
  behavior. This does not establish universal case authorization.
- `InvestigationService` audits case/network access but does not itself enforce
  per-case assignments. `/api/v1/graph/*` has no principal dependency in its
  router. Nexus global/batch/path and review/reset routes use a principal but
  lack a common resource-scoping policy. Neo4j must not expand access; durable
  graph mode needs explicit authorization tests, not reliance on graph proximity.
- `config.py` has Neo4j URI/user/password settings but no graph-backend selector,
  projection revision, explicit Neo4j database selection, or projection status.
  `main.py` calls load_dotenv and constructs `app = create_app()` at import time.
  PostgreSQL is selected by repository name **or** the URL containing "postgres";
  initialization failure falls back to memory. Selecting "neo4j" is not implemented.
- Startup creates the registry/pipeline, graph wrapper, and ingestion service;
  no Neo4j driver lifespan/shutdown/close or sync worker exists.
- Core and system routers both register `/health` (and prefixed equivalents);
  core is mounted first. These are liveness responses, not dependency probes.
  `/ready` always reports ready and storage=in_memory from dictionary counts;
  `/system/status` also reads counts, not database connectivity or synchronization.
  Existing `api/errors.py:ExternalServiceUnavailableError` maps to the established
  HTTP 503 error envelope and can be reused for sanitized dependency failures.
- Relevant tests: `tests/ingestion/`, `tests/services/test_ingestion_service.py`,
  `tests/graph/`, entity/fusion/pathfinder/evidence/auth/system-health API tests,
  and frontend ingestion/network/fusion suites. No Neo4j database integration
  suite or dedicated two-database test harness was found. Existing tests do not
  demonstrate PostgreSQL durability or cross-database consistency.

### Credential audit — values deliberately omitted

Current tracked HEAD was inspected with filename-only patterns and a script
that reads Git blobs and emits only file/line/classification. No exposed
credential was used to authenticate or connect. This was a current-tree scan,
not an exhaustive historical or entropy-based secret audit.

| Affected file | Finding |
| --- | --- |
| `.env.example:4` | Non-placeholder remote PostgreSQL credential committed in a connection URI. |
| `backend/app/config.py:41` | Non-placeholder remote PostgreSQL credential embedded as the default URL. |
| `backend/app/config.py:46,50`, `backend/app/auth/verifier.py:57` | Hardcoded development Neo4j/JWT authentication defaults. |
| `docker-compose.yml:9,25,47`, `.env.example:6`, `configs/.env.example:6` | Local/example database or authentication defaults. They are publicly known values, not deployment secrets. |
| `docs/DEPLOYMENT_AUDIT.md:123` | Remote connection example uses a password placeholder; not classified as an additional exposed password. |

**The credential owner must rotate the exposed remote database credential.**
Remove live defaults from source/templates in a separately authorized change,
and replace any deployed authentication secret that reused committed defaults.
Deleting text alone does not revoke exposed credentials. No secrets were changed,
no history was rewritten, and no rotation was attempted by this audit.
Provider-key defaults inspected in config.py are empty; pattern searches found
no matching provider API token or private-key marker in the scanned source set.

### Executed baseline checks

Environment: Windows/PowerShell; Python 3.13; pytest 8.4.2; Ruff 0.16.4;
NetworkX 3.6.1; FastAPI 0.129.0; psycopg 3.3.4; Node 22.18.0; npm 10.9.3.
Packages were already available; no dependency installation was performed.

Backend checks ran through a temporary audit harness outside the tracked tree:
`%TEMP%/nexus_step1_baseline.py`. It sets memory mode, an empty DATABASE_URL and
STATE_PATH, the repository's synthetic artifact, development auth, and inert
AI/Neo4j settings. It disables dotenv loading and Settings' env-file source,
blocks psycopg.connect and outbound Python sockets, and allows only the stdlib
socketpair construction required by Windows asyncio. These controls prevent
import-time app construction from contacting the configured remote database.
This is an explicitly selected memory baseline, not a mock substitution for
selected Neo4j mode. No database integration test or cleanup was run.

Frontend checks used `VITE_API_BASE_URL=http://127.0.0.1:1/api/v1`; test invocation
also set `VITE_USE_MOCKS=true`. Tests use their existing mocks/fixtures; this
does not demonstrate a live frontend-to-database path. Build generated local
ignored `frontend/dist` assets; it did not publish them.

| Command actually executed | Status and result |
| --- | --- |
| `python -m ruff check backend/ shared/ tests/ --output-format concise` | PASSED, exit 0: all checks passed. |
| `python <temporary audit harness> pytest` (corrected harness, approved sandbox retry) | PASSED, exit 0: **669 passed, 1 skipped, 2 warnings**, 124.52 s. Harness invokes `pytest.main(["-q", "--tb=short", "-o", "addopts="])` over configured tests/. |
| `python <temporary audit harness> pytest tests/test_entity_api.py tests/test_evidence_api.py -rs` | PASSED, exit 0: 33 passed, 1 skipped, 6.92 s. Clarifies skip at `tests/test_evidence_api.py:313`: no evidence items available. The skipped assertion was NOT RUN. |
| `python <temporary audit harness> ground-truth` | PASSED, exit 0: executes `scripts/evaluate_ground_truth.py`; TP=2, FP=0, FN=0; precision/recall/F1=100%. This small benchmark is not a database parity test. |
| `npm test -- --run` in frontend (approved sandbox retry) | PASSED, exit 0: **18 files, 108 tests**, 70.60 s. React Router future-flag warnings remain. |
| `npm run build` in frontend (approved sandbox retry) | PASSED, exit 0: TypeScript and Vite production build; Vite phase 59.01 s. |
| `npm run lint` in frontend | FAILED, exit 1: **24 errors, 39 warnings**. Existing React hook/purity/effect and other lint findings; representative failures include Patterns.tsx:98 and Timeline.tsx:68. No runtime source was changed to fix them. |
| `git diff --check` after documentation edit | PASSED when finalized below; no whitespace errors. |
| Live PostgreSQL/Neo4j integration, Neo4j Cypher execution, durable restart/failure tests | NOT RUN: no dedicated database pair was provisioned or contacted in this audit. |

Pre-existing warnings: backend JWT test fixtures use a short HMAC key (two
InsecureKeyLengthWarning messages); frontend React Router emits future-flag
warnings. The valid isolated backend run had no failed application tests.

Earlier attempts, separated from application failures:

- Initial backend guard blocked Windows socketpair creation and sandbox access
  denied pytest temporary directories: 103 failed, 546 passed, 21 errors. This
  attempt is **BLOCKED/invalid as an application baseline**, not 103 proven
  product regressions. Corrected the temporary harness and reran with approved
  sandbox escalation; the successful complete result above supersedes it.
- Initial frontend test/build attempts were **BLOCKED** by esbuild directory
  access while loading vite.config.ts. Approved retries passed.
- A few exploratory searches used nonexistent paths/globs; actual files were
  located with rg. One classification helper hit a Windows decoding error;
  the UTF-8 retry completed. An overly broad AST filesystem walk was interrupted;
  the replacement restricted inspection to `git ls-files` and completed.

Local command logs remain in `%TEMP%` as `nexus_step1_ruff.log`,
`nexus_step1_pytest_retry.log`, `nexus_step1_skip_detail.log`,
`nexus_step1_ground_truth.log`, `nexus_step1_vitest_retry.log`,
`nexus_step1_build_retry.log`, and `nexus_step1_frontend_lint.log`.
They are audit artifacts, not committed fixtures or CI infrastructure.
Repository discovery commands included `git status --short`,
`git branch --show-current`, `git rev-parse HEAD`, `git log -1`,
`git merge-base HEAD origin/main`, `git ls-files`, targeted `git show HEAD:<file>`
through value-suppressing scripts, `rg --files`, `rg -n`, Get-Content,
Get-ChildItem/Get-Command, and AST/package-metadata inspection. No remote Git
operation or database command was executed.

### Implemented / partial / missing feature matrix

| Capability | Status | Evidence/qualification |
| --- | --- | --- |
| CSV parsing, normalization, deterministic ER and bundle validation | IMPLEMENTED | Working memory tests; process-local registry limitations above. |
| PostgreSQL storage adapter and raw schema | PARTIAL | Actual SQL exists; commit errors, reload completeness, and transactional boundaries need correction. |
| In-memory GraphStore and NetworkX intelligence | IMPLEMENTED | Existing algorithms exercised by baseline suite. |
| Lossless graph metadata at every boundary | PARTIAL | Domain model has fields; operational exports/API serializers drop or rewrite them. |
| Neo4j Docker/config declarations | PARTIAL | Image `neo4j:5.20-community`, volume and APOC declaration exist; runtime integration absent. |
| Neo4j Python dependency/driver lifecycle | MISSING | No manifest entry, installed driver, connection or close path. |
| Neo4j schema, writes, reads and rebuild | MISSING | GraphRepository database loader is a stub. |
| Transactional projection revision and retry | MISSING | No durable sync marker/outbox or applied-version check. |
| Consistent graph read selection | PARTIAL | Shared wrapper plus direct GraphStore and raw-dictionary paths. |
| Evidence authorization | PARTIAL | Policy/tests exist; case/global/graph access not universally enforced. |
| Readiness/outage/lag reporting | MISSING for Neo4j | Current health routes do not verify dependencies. |
| Durable review/merge/audit restart parity | PARTIAL | Separate SQL operations and incomplete round trips. |
| Dedicated local graph integration tests | MISSING | Memory unit/API baseline passes; no Neo4j integration baseline. |

### Smallest proposed implementation (not implemented)

Keep PostgreSQL as the authoritative repository and keep the NetworkX algorithms
and public response shapes. Add an explicit graph read backend, not a competing
Neo4j system of record. Start with a full-snapshot projection because the existing
application already materializes the complete graph; avoid introducing a queue
framework or rewriting deterministic algorithms in Cypher.

1. Correct the authoritative commit boundary first: persist bundle/review data
   and the associated mutation audit atomically, then publish memory state.
   Do the same for review decision plus merge. Raise sanitized storage errors
   rather than returning successful counts on failure. Preserve complete record,
   provenance, decision and audit payloads in PostgreSQL; repair restart loading.
2. Add a monotonic PostgreSQL graph revision row, incremented in each graph
   mutation transaction, and durable batch membership. This is the minimal
   durable dirty marker for full rebuilds, not a promise of cross-database ACID.
   Read the graph and its revision in one consistent PostgreSQL snapshot.
3. A small synchronizer serializes projection writers, copies that snapshot
   into a NEXUS-scoped Neo4j projection, and commits the applied revision with
   the graph in one Neo4j transaction. Full replacement must remove stale edges
   and merged/deleted nodes only within the owned projection. A failure leaves
   the prior complete projection; the PostgreSQL revision remains ahead and
   signals pending work. Retry at startup/after mutations and through an explicit
   local sync command; use database-level serialization to prevent older writers
   overwriting newer revisions. A later incremental outbox is an optimization.
4. Preserve stable application node/edge IDs, endpoint direction and parallel
   edges. Use a fixed NEXUS node label and relationship type with domain
   entity_type/edge_type properties to avoid dynamic Cypher identifiers. Store
   full canonical payload JSON alongside selected indexable scalar fields;
   never stringify arbitrary objects silently or regenerate IDs/timestamps.
   Preserve nulls, nested provenance, source references, derivation class,
   confidence, weight, storage mode, temporal fields and arbitrary domain data.
5. Make the selected graph reader return both a lossless graph snapshot and a
   compatible GraphStore. Operational `to_graph_store()` delegates in Neo4j mode;
   the shared GraphRepository and direct global/batch graph serializers use the
   same reader/revision. Source records, case permissions, reviews and audits
   remain PostgreSQL reads. Static demo records must be explicitly sourced from
   the synthetic authoritative dataset for this mode, not appended as fallback.
6. Compare authoritative and applied revisions for graph reads; initially fail
   closed with the existing sanitized 503 envelope while unavailable or behind.
   This prevents silent stale-memory substitution. A committed upload with a
   pending projection must report persistence success separately from
   graph_updated/graph_ready=false, with an existing warning mechanism. Do not
   report graph readiness from row counts alone or falsely report PostgreSQL
   rollback when only Neo4j failed. Preserve existing successful contracts.
7. Initialize and close one driver through app lifecycle, specify the database
   explicitly, bound timeouts/retries, and report storage/graph availability,
   authoritative/applied revision and lag in readiness. Keep liveness independent.
   Keep the current memory implementation available only when explicitly selected.

Proposed interfaces and files (all names below are prospective):

| File/interface | Responsibility |
| --- | --- |
| `backend/app/db/graph_projection.py` | `GraphSnapshot(revision,nodes,edges)`, `ProjectionStatus`; small `GraphReader.read_snapshot()/to_graph_store()/status()` and `GraphProjection.replace_snapshot()/close()` protocols. |
| `backend/app/db/neo4j.py` | Official-driver adapter, parameterized Cypher, schema setup, lossless snapshots, atomic scoped replacement and revision reads; sanitized errors, no silent fallback. |
| `backend/app/db/ingestion/graph_adapter.py` (extend) | One shared complete metadata codec for typed bundles/raw records/GraphStore; reuse existing mapping logic. |
| `backend/app/services/graph_projection_service.py` | Consistent PostgreSQL snapshot export, serialized sync/retry and applied-revision checks. |
| `backend/app/db/postgres.py`, `schema.sql`, `db/migrations/` | Reliable transactional mutation APIs, full payload persistence, graph revision and batch membership, idempotent schema upgrade using the actual runtime schema path. Do not assume the legacy migration CLI executes SQL. |
| `backend/app/services/ingestion_service.py`, `db/ingestion/pipeline.py`, `resolution/registry.py` | Stage/rebuild identity registry from committed records; commit before publishing registry/graph; no mutation of shared registry on failed ingestion. |
| `backend/app/api/nexus_routes.py`, `services/audit_service.py` | Route decisions/merges through atomic repository operation; durable audit and decision metadata; selected graph reader for raw graph endpoints. |
| `backend/app/core/graph/repositories/graph_repository.py`, `api/dependencies.py`, `db/in_memory.py` | Preserve analytical interface; fix misplaced helpers only if retained/used, remove misleading stub semantics, unify selected read provider. |
| `backend/app/config.py`, `main.py`, `api/system_routes.py`, dependency manifests | Explicit graph selection, validation, lifespan, safe defaults, readiness/lag and driver dependency. |
| `scripts/rebuild_graph_projection.py` | Explicit rebuild/retry entry point; require an identified target, never infer a shared database from committed defaults. |
| `tests/graph/`, `tests/ingestion/`, proposed `tests/integration/test_neo4j_projection.py`, `docker-compose.test.yml` | Metadata parity, rollback/restart, graph-reader routing, lag/outage tests with dedicated local PostgreSQL and Neo4j containers and isolated volumes/ports. |
| Frontend hooks/status handling, only if required | Preserve current response rendering; invalidate all case/entity/global graph keys after mutation and display existing graph-ready/error state honestly. No graph UI redesign. |

### Official compatibility evidence and boundaries

No package or server was installed/selected for deployment in this audit. The
repository currently declares Neo4j **5.20 Community**. A candidate official
Python driver **6.x** is compatible at the documented series level: the
[driver installation manual](https://neo4j.com/docs/python-manual/current/install/)
supports Neo4j 5.x and requires Python >=3.10; this repository requires >=3.11
and the local interpreter is 3.13. Exact driver patch/image pins must be chosen
and verified against release notes before implementation, then exercised together
in the dedicated test pair. This is not a live compatibility certification.

Use parameterized queries and managed `execute_read`/`execute_write` callbacks;
callbacks must tolerate retries and sessions must specify the database. See
[official transaction guidance](https://neo4j.com/docs/python-manual/current/transactions/).
Cypher 5 documents MERGE, including stable-pattern and uniqueness considerations:
[Cypher 5 MERGE](https://neo4j.com/docs/cypher-manual/5/clauses/merge/).
No APOC or GDS functionality is needed for the proposed initial projection.

Nested maps cannot be stored directly as graph properties; the JSON payload
strategy follows [official property-type constraints](https://neo4j.com/docs/cypher-manual/current/values-and-types/property-structural-constructed/).
Use uniqueness constraints and application validation, avoiding Enterprise-only
existence/type/key constraints per [official constraint documentation](https://neo4j.com/docs/cypher-manual/current/schema/constraints/create-constraints/).
The attempted version-5 managing-constraints URL was unavailable; exact DDL must
be verified on the selected 5.20 test server before claiming it works. Do not
copy newer dynamic-label/Cypher features merely because current docs show them.

### Acceptance criteria and risks for subsequent steps

- Memory-mode API and deterministic algorithm baseline remains passing; no
  guilt/probability-of-criminality outputs or proximity-as-proof claims.
- Dedicated local PostgreSQL/Neo4j fixtures require explicit opt-in and ownership
  checks before cleanup; do not use root compose defaults or a team database.
  Unit tests must remain unable to contact a live database at import time.
- Ingest, restart both stores, rebuild Neo4j from PostgreSQL, and compare node
  and edge IDs, directions, parallel edges, complete metadata and evidence
  references. Source records, review decisions and audit integrity survive restart.
- Failed PostgreSQL writes change neither authoritative records nor published
  registry/cache state. Successful commit followed by Neo4j failure is recoverable
  and explicitly pending. Replay after worker/process crash is idempotent.
- CONFIRM/REJECT/DEFER and merge/update/delete/reset invalidate the correct
  projection revision. Merges preserve edge IDs/provenance while redirecting
  endpoints, remove stale projection nodes, and maintain canonical registry state.
- A selected Neo4j outage, missing driver/config, invalid credentials or lag
  must never return memory/demo graph success. Readiness and graph_ready agree
  with the committed projection revision; error messages contain no secrets.
- Cover every graph read family, including global, batch, case/entity,
  Pathfinder, intelligence, evidence paths, and copilot tools. Cache keys must
  include/reconcile revision; deny unauthorized case traversal before returning data.
- Compare existing NetworkX outputs on the same snapshots; Neo4j persistence
  must not change the algorithms or turn parallel evidence into a single edge.
- Test duplicate CSV replay, multi-process writers, transaction failure, malformed
  payloads, empty graphs, relationship direction changes, and complete metadata
  round trips on the selected driver/server/Cypher versions.

Principal risks are pre-existing false-success PostgreSQL writes; lossy metadata
before projection; divergent graph/dictionary/demo read paths; non-durable ER
registry and decision/audit payloads; missing universal case authorization;
unsafe remote configuration/reset defaults; and O(V+E) full rebuild latency.
The full-snapshot design minimizes initial machinery, but scale/latency must be
measured before promising large-dataset throughput. Passing memory tests alone
does not resolve these risks. Frontend lint failures are a separate baseline debt.

Suggested commit message:
`docs(neo4j): document integration audit and test baseline`

---

The following step-0 record is historical and is superseded by the step-1
checkout, findings and executed checks above.

## Step 0 — verified repository baseline (2026-09-07)

Inspected `AGENTS.md`, `PROGRESS.md`, dependency manifests, PostgreSQL storage,
graph representation, migration directory, and Neo4j references in the checkout.
Branch: `feat/neo4j-integration`.
Commit: `952bcb95fefb306f7281815785ed39f48ef476ec`.
The initial working tree was clean. The merge base with the local `origin/main`
reference is the same commit; remote freshness was not checked.
No branch switch, fetch, reset, commit, push, or deployment was performed.

### Actual implementation

- `backend/app/db/postgres.py` persists nodes, edges, source records, review
  candidates, batches, and audit events and maintains in-memory indexes.
- Its `to_graph_store()` exports nodes and directed relationships for existing
  graph algorithms. Relationship properties currently retain only weight and
  provenance: this export is insufficient as a lossless projection source.
  Stored edges also include stable IDs, source references, derivation class,
  confidence, temporal bounds, and domain properties.
- `backend/app/core/graph/algorithms/utils.py` defines `GraphStore`, `NodeRecord`,
  and directed `AdjEdge` records. NetworkX algorithms already consume this layer.
- `backend/app/config.py` contains Neo4j connection settings, and
  `docker-compose.yml` declares Neo4j `5.20-community`. These declarations do
  not establish a working runtime integration.
- Neither `pyproject.toml` nor `backend/requirements.txt` declares a Neo4j driver.
- Existing database schema locations include `backend/app/db/schema.sql` and
  `backend/app/db/migrations/schema.py`.

### Constraints for subsequent implementation

PostgreSQL remains authoritative; Neo4j is a rebuildable projection. Preserve
API contracts and deterministic algorithms. Preserve complete relationship
identity, direction, references, provenance, derivation, and metadata. Selected
Neo4j mode must report outages and synchronization lag without silent fallback.
Use synthetic data and dedicated local test databases only. Never include
credentials in documentation or logs. No commits without explicit authorization.

### Validation and limitations

- PASSED: `git status --short` (initially empty), `git branch --show-current`,
  `git rev-parse HEAD`, `git log -1 --format='%h %s'`, and
  `git merge-base HEAD origin/main`.
- Executed: `Get-Content`, `Get-ChildItem`, `rg --files`, and targeted `rg -n`
  inspections of the files and directories listed above.
- FAILED: an initial search used nonexistent `backend/app/dependencies.py` and
  `backend/app/core/config.py`; the actual configuration path was subsequently
  located at `backend/app/config.py`.
- NOT RUN: backend/frontend tests, lint, builds, ground-truth benchmark, database
  connections, and integration tests. Historical counts in `PROGRESS.md` are
  not independently verified test results.
- NOT RUN: official driver/server/Cypher compatibility verification; no driver
  or Cypher implementation has been selected or added in this baseline step.
- Runtime integration, synchronization, failure behavior, and local database
  isolation remain unimplemented and unverified by this step.

Suggested commit message: `docs: record verified Neo4j integration baseline`.
