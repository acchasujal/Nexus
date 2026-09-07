# Neo4j implementation record

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
