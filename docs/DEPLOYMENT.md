# NEXUS Deployment Guide

This guide covers deployment architectures, cloud hosting instructions, configuration parameters, and verification procedures for NEXUS.

---

## 1. Minimal Public SIH Demo Architecture

For public hackathon demonstrations, NEXUS supports an ultra-lightweight deployment topology:

```
                    INVESTIGATOR / JUDGE BROWSER
                                 │
                 ┌───────────────┴───────────────┐
                 │ HTTPS (Static UI)             │ HTTPS (API Calls)
                 ▼                               ▼
     ┌───────────────────────┐       ┌───────────────────────┐
     │        VERCEL         │       │        RENDER         │
     │  React 19 / Vite SPA  │       │    FastAPI Backend    │
     │  (Global CDN & SPA    │       │ (Uvicorn on Free Tier │
     │   Rewrite Routing)    │       │   $PORT & 0.0.0.0)    │
     └───────────────────────┘       └───────────┬───────────┘
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                 ┌───────────────────────────────┐ ┌───────────────────────────┐
                 │  In-Memory GraphStore         │ │  BSA Section 63 Proofs    │
                 │  445 Nodes, 530 Edges         │ │  SHA-256 Provenance       │
                 │  Zero Cloud DB Required       │ │  Cryptographic Evidence   │
                 └───────────────────────────────┘ └───────────────────────────┘
```

> **Note:** Standalone demo mode boots completely in `<6ms` from the bundled synthetic dataset without mandatory external PostgreSQL or Neo4j instances.

---

## 2. Enterprise Cloud Architecture

In full production or multi-station enterprise setups:
- **Relational Storage:** PostgreSQL 16 on Render or Neon for case registries, RBAC, and audit trails.
- **Graph Storage:** Neo4j AuraDB or containerized Neo4j 5 Community for durable Cypher projection.
- **Backend Service:** Render Docker Web Service or Kubernetes cluster.
- **Frontend SPA:** Vercel edge deployment with global CDN caching.

---

## 3. Step-by-Step Deployment Protocol

### Part A: Deploy FastAPI Backend on Render
1. Log into [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect repository: `https://github.com/acchasujal/Nexus` (or fork).
4. Configure parameters:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
5. Configure Environment Variables:
   | Variable | Recommended Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables production settings |
   | `AUTH_MODE` | `demo` | Enables role-switching in demonstration mode |
   | `CORS_ORIGINS` | `https://your-nexus.vercel.app` | Comma-separated allowed frontend domains |
   | `NEO4J_URI` | *(optional)* `neo4j+s://...` | Neo4j AuraDB URI |
   | `NEO4J_USERNAME` | *(optional)* `neo4j` | Neo4j user |
   | `NEO4J_PASSWORD` | *(optional)* `secret` | Neo4j password |

### Part B: Deploy React Frontend on Vercel
1. Log into [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** $\rightarrow$ **Project**.
3. Import the repository and configure:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Environment Variables:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://nexus-backend.onrender.com` | Base URL of deployed Render backend |

---

## 4. Pre-Flight Readiness Checklist

- [x] Clean working tree on `main` branch.
- [x] Zero hardcoded secrets, API tokens, or `.env` files committed.
- [x] Root `/health` liveness probe endpoint returns `200 OK`.
- [x] Root `/ready` readiness probe endpoint operational.
- [x] Frontend SPA rewrite rule (`/*` $\rightarrow$ `/index.html`) enabled via `vercel.json`.
- [x] Dynamic production CORS origin parsing verified.
- [x] Ground-truth precision/recall benchmark verified at 100%.

## Neon database and private evidence storage (EXTENSION)

The existing project `delicate-frost-27919131` uses branch `production` in
`aws-us-east-2`. `neon.ts` declares the private `object` bucket and the standalone
`api` hello function. NEXUS continues to run its Python API on Render; the hello
function does not serve investigative data. PostgreSQL uses the existing psycopg
repository and bounded connection pool. Schema initialization uses the direct URL,
and runtime queries use the pooled URL. Neo4j remains the complementary graph
projection. Repository reads stay available while that projection is degraded;
live graph operations report an explicit unavailable state.

Copy these values from the ignored `backend/.env` into Render's environment:

| Key | Source/value |
| --- | --- |
| `DATABASE_URL` | Neon pooled connection string |
| `DATABASE_URL_UNPOOLED` | Neon direct connection string |
| `NEXUS_REPOSITORY` | `postgres` |
| `EVIDENCE_STORAGE_BACKEND` | `s3` (Neon's S3-compatible API) |
| `EVIDENCE_BUCKET` | `object` |
| `AWS_ENDPOINT_URL_S3` | Neon Object Storage endpoint |
| `AWS_ACCESS_KEY_ID` | Neon storage access key |
| `AWS_SECRET_ACCESS_KEY` | Neon storage secret |
| `AWS_REGION` | Neon generated signing region |

The AWS-prefixed keys configure the compatible client; they do not require an AWS
account or AWS bucket. Keep existing `NEO4J_*` settings. Source bytes are stored in
the private bucket under SHA-256 content-addressed keys; document metadata and
hashes are stored in PostgreSQL. Authorized downloads verify the stored hash and
record an audit event. No public object URLs are returned.

Project-local Neon skills are installed in `.agents/skills/`; their provenance is
in `skills-lock.json`. `.codex/config.toml` adds the project-scoped OAuth MCP
endpoint. CLI sign-in and MCP authentication are separate; reconnect/authenticate
the MCP client if its tools are not available. Generated `.neon` and `.env*.local`
files are ignored. Existing global Codex providers and configuration are preserved.


### Cold-start initialization (2026-10-05)
Production defaults to background graph startup. NEO4J_BACKGROUND_STARTUP=true explicitly enables it (declared by the Render blueprint); false opts into blocking graph startup. Development retains blocking startup by default. PostgreSQL schema/hydration and audit bootstrap remain mandatory. HTTP then serves canonical reads and login while Neo4j connects, validates schema, syncs and reads its durable projection. /health is liveness; required /ready stays 503 until graph readiness. Live graph mutations/reads stay gated. Failure does not switch to an in-memory graph. Background work is canceled and awaited on shutdown.
Startup logs emit elapsed_ms for PostgreSQL connection, schema, hydration, index rebuild, audit bootstrap, Neo4j connection, schema, sync, read, graph total and factory-to-HTTP readiness. Factory timing excludes earlier Python imports and platform process scheduling; compare Render process timestamps for end-to-end cold-start time. Schema DDL remains unchanged because the current additive schema strategy has no verified cheaper version check.
The lightweight frontend queries and login allow three attempts, each with a 20s request deadline, and backoffs of 2s then 40s. Immediate proxy 503s therefore get a final attempt after 42s; hung requests finish within about 102s. No infinite polling or new warm-up service was added. Secondary intelligence remains activated by its tab; graph analytics does not block first paint.
Production cold verification must use a clean browser, an actually cold Render instance, and no refresh. Local simulation alone does not establish production recovery or startup improvement.

Readiness also reports `startup.factory_to_http_ready_ms` (excludes earlier imports/platform scheduling) and `graph_initialization` status, stage, elapsed_ms and sanitized exception type if initialization fails. These diagnostics contain no credential or exception-message data and do not replace operational graph readiness.


Production diagnostics from 03eb4a7 established factory-to-HTTP readiness at 11790.1ms and initial graph connection failure (stage=connect, 6592.9ms), while a later readiness probe connected successfully. Initialization had stopped before schema/sync/read. Background initialization now permits at most three connection attempts with 2s/4s backoff, reusing the existing driver when available. Schema/sync/read run once only after connection success; exhausted retries keep live graph routes gated. Blocking development/explicit-false startup preserves the required failure policy. This recovery addresses observed connection-stage failure and does not aggressively retry expensive graph work. Factory timing excludes prior imports and is not the full Render cold-start interval.


### Production first paint and asset integrity (2026-10-05)
The frontend imports `backend/app/db/canonical_read_model.json` through one `DEMO_BASELINE` adapter. Bootstrap KPIs, pulses, and Worklist initially display that versioned synthetic snapshot with an explicit demo-baseline/syncing label. It is never inserted as successful query-cache data. Confirmed API responses replace it, including legitimate empty results. Permission refusals remain errors and suppress fallback details.
Affected intelligence reads and Worklist share three attempts for 502/503/504, transport failure, or timeout, with 2s/40s backoff and 20s request deadlines. An active exhausted query gets at most one additional request after another recovering read succeeds. Disabled tabs stay dormant. Retry exhaustion retains labelled baseline or last confirmed data; focus, reconnect, and explicit retry remain available. Session transitions clear the query cache to prevent retaining another officer's results.
Current production HTML referenced `Worklist-D3JDnS2I.js`; the reported older `Worklist-C4i2wvt8.js` and `DataTable-Bmd_hf_2.js` returned 404. Existing HTML revalidation did not protect already-running tabs. Vercel immutable deployment URLs redirect anonymous users to Vercel login, so cross-origin immutable asset pinning is unsuitable here. Vercel platform Skew Protection requires Pro/Enterprise and does not list plain Vite as a supported framework (https://vercel.com/docs/skew-protection).
The build now preloads generated JS modules from the same deployment into the browser module map, with secondary preloads at low fetch priority. React route evaluation remains lazy. SPA documents use `no-store, max-age=0`; hashed assets use one-year immutable caching and remain excluded from SPA rewrites. A build manifest and mandatory `verify-build.mjs` check reject missing assets/dependencies or secondary modules omitted from preloads. A Vite preload-error listener allows at most one automatic reload per build for an initial-download/deployment race; persistent failure reaches the existing boundary. See https://vite.dev/guide/build#load-error-handling.
Tradeoff: secondary route code downloads earlier; network/backend hydration still happens only when the route/tab is used. Local Chrome verified 1.07s baseline visibility while APIs returned 503 and zero late asset requests/page errors when navigating Worklist, Timeline, and Settings after all asset URLs were blocked and HTTP caching was disabled. This is local evidence, not an idle-production measurement. Production verification must record actual timings, module responses, automatic reconciliation, and login without refresh.
Startup retains mandatory repository and audit work and the existing background graph lifecycle. New timings cover module imports, storage/pipeline/audit preparation, and router/service registration, exposing previously unmeasured gaps. No database schema, graph policy, audit invariant, or startup-order changes were justified by the supplied working-Neo4j logs.

The additional startup stage durations are also available in `/ready.startup` for production verification without exposing logs or credentials.
