# Development guide

> Reviewed 2026-10-28. CURRENT setup instructions; deployment-specific observations belong in [progress](../progress.md).

## Prerequisites

- Python 3.11+ as declared in [pyproject.toml](../pyproject.toml). CI uses 3.11; recent local checks used 3.12 x64. Do not assume every newer Python/ARM combination has compatible dependency wheels.
- Node 22.12+ is recommended. CI uses Node 20; the installed toolchain requires a sufficiently recent patch release.
- Git. Docker is optional for local database services.

Install backend dependencies from [backend/requirements.txt](../backend/requirements.txt) and frontend dependencies with `npm ci` in `frontend/`. Root npm dependencies support optional Neon infrastructure configuration, not the React build.

## Local application

From the repository root:

```sh
python -m venv .venv
```

Activate the environment:

| Shell | Command |
| --- | --- |
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Linux/macOS | `source .venv/bin/activate` |

```sh
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`; OpenAPI is at `http://localhost:8000/docs`. On Windows with script-execution restrictions, use `npm.cmd` in place of `npm`.

Default settings use the checked-in synthetic artifact with an in-memory repository and graph. No LLM key is required for deterministic fallback behavior. Do not connect a development session to a shared production database unintentionally.

## Environment configuration

[.env.example](../.env.example) is the minimal local template. [backend/.env.example](../backend/.env.example) provides additional examples. Copy a template into an ignored `.env` only when configuring a fresh local environment; preserve an existing file and its private values.

Backend configuration is defined by [Settings](../backend/app/config.py). The root launch reads the root environment; do not assume an arbitrary nested `backend/.env` is loaded by every command.

| Setting | Local default / purpose |
| --- | --- |
| `ENVIRONMENT` | `development` |
| `NEXUS_REPOSITORY` | `memory`; select `postgres` only with a private `DATABASE_URL` |
| `GRAPH_BACKEND` | `memory`; select `neo4j` with valid URI, user, password, and database |
| `AUTH_MODE` | `demo`; this is not a production identity provider |
| `JWT_SECRET_KEY` | Development can generate an ephemeral process key; production validation requires a private configured key |
| `ARTIFACT_PATH` | Defaults to `artifacts/nexus_graph/nexus_graph.json` |
| `STATE_PATH` | Optional local state file; use an ignored runtime directory |
| `VITE_API_BASE_URL` | Frontend API origin; local development file points to port 8000 |
| `VITE_ENABLE_MOCKS` | `false` in the checked-in development configuration |

Officer selection requires server authentication and opens `/intelligence`. The former `VITE_DEMO_MODE` flag is retired and ignored. Restart Vite after changing frontend environment values. Vite values are public build inputs: never put secrets in them.

## Optional local databases

[Compose](../docker-compose.yml) declares PostgreSQL and Neo4j with private passwords supplied through the local environment. It binds ports to loopback and uses named volumes.

```sh
docker compose up -d postgres neo4j
```

Set private `POSTGRES_PASSWORD` and `NEO4J_PASSWORD` values first. PostgreSQL exposes 5432; Neo4j exposes Browser on 7474 and Bolt on 7687. There is no shared default password.

The frontend container recipe/build context has not been revalidated for the current cross-directory snapshot inputs. Use the native frontend quick-start above; do not describe full `docker compose up --build` as a verified turnkey path. See [deployment](DEPLOYMENT.md).

## Verification commands

Run from the root unless indicated:

```sh
python -m ruff check backend/ shared/ tests/
python -m pytest
python scripts/evaluate_ground_truth.py
npm --prefix frontend run lint
npm --prefix frontend run test:run
npm --prefix frontend run build
```

Focused recovery checks:

```sh
python -m pytest tests/test_cold_start_lifespan.py tests/test_auth_verifier.py tests/test_evidence_object_storage.py
npm --prefix frontend run test:run -- src/tests/DemoEntry.test.tsx src/tests/OfficerLogin.test.tsx src/tests/RecoveryPolicy.test.tsx
```

Test totals change with implementation. [progress.md](../progress.md) records dated results, including existing failures; CI output is authoritative for its own revision and environment. Do not weaken assertions or replace failures with empty data to obtain a green run.

On Windows, if a default temporary directory is inaccessible, use a fresh writable directory with `python -m pytest --basetemp <new-temporary-directory> -p no:cacheprovider`. Keep test logs outside the repository.

## Synthetic artifacts

The checked-in base graph contains 445 nodes and 486 edges. Runtime enrichment can produce different counts; a stored deployment is not identical to an untouched artifact.

Regeneration **overwrites generated fixture files**. Review the generator and use a disposable checkout when experimenting:

```sh
python -m synthetic_data.nexus_generator --demo
python scripts/evaluate_ground_truth.py
python scripts/verify_canonical_invariants.py
```

The generator also updates `backend/app/db/synthetic_graph.json`. [generate_read_model.py](../scripts/generate_read_model.py) maintains the canonical intelligence read model; its regeneration changes timestamps/checksums and should be deliberate.

The frontend build independently derives ten initial worklist rows from the synthetic graph:

```sh
node frontend/scripts/generate-demo-snapshot.mjs
node frontend/scripts/generate-demo-snapshot.mjs --check
```

It validates the demo profile and seed and uses a normalized source checksum. Do not manually edit [demoEntrySnapshot.json](../frontend/src/lib/demoEntrySnapshot.json).

## Seeding, reset, and migrations

Inspect [seed_production_demo.py](../scripts/seed_production_demo.py), [migrate_to_postgres.py](../scripts/migrate_to_postgres.py), and [migrate_to_neo4j.py](../scripts/migrate_to_neo4j.py) before running them. A script name is not proof of its target: confirm which repository/connection it constructs and whether a dry run writes anything.

The UI demo reset is a backend mutation, not a local snapshot toggle. It requires an appropriate server session and can be gated by graph readiness. Do not reset a shared deployment merely to prepare a screenshot.

## Documentation and changes

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md). Extend existing algorithms and shared contracts. Update the relevant canonical guide, `progress.md`, and `decisions.md` when applicable. Historical plans live in [archive](archive/README.md), not alongside current specifications.
