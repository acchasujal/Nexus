# Deployment and operations

> Reviewed 2026-10-28. CURRENT deployment topology and explicit limitations. Dated observations are in [progress.md](../progress.md).

## Evaluation topology

| Component | Location / role |
| --- | --- |
| Frontend | [Vercel evaluation login](https://nexus-eight-weld-33.vercel.app/login) |
| API | `https://nexus-4djk.onrender.com` on Render |
| Application repository | PostgreSQL when configured; in-memory mode for standalone development |
| Graph projection | Neo4j with explicit connectivity/projection gates |
| Evidence source bytes | Optional private S3-compatible object storage |
| Demo snapshot | Static build inputs; independent of API readiness |

This is a public synthetic-data demonstration, not a production law-enforcement deployment. See [security limits](SECURITY.md), especially the demo identity implementation.

## Render API

The current [blueprint](../render.yaml) uses:

```text
Build: pip install -r backend/requirements.txt
Start: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
Health check: /health
```

Configure settings privately through the hosting environment:

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | Production configuration validation |
| `AUTH_MODE` | Current demo verifier behavior; not an identity-provider integration |
| `JWT_SECRET_KEY` | Private signing key; never a Vite value |
| `CORS_ORIGINS` | Intended frontend origins; inspect middleware preview patterns too |
| `NEXUS_REPOSITORY` | `postgres` for the persistent deployment |
| `DATABASE_URL` | Runtime PostgreSQL connection |
| `DATABASE_URL_UNPOOLED` | Optional direct/schema-initialization connection |
| `ARTIFACT_PATH` | Synthetic graph input |
| `GRAPH_BACKEND` | `neo4j` or explicit standalone `memory` |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | Graph connection configuration |
| `NEO4J_BACKGROUND_STARTUP` | Explicitly stage graph initialization after HTTP readiness |
| `NEO4J_FAILURE_POLICY` | Required versus degraded readiness policy |
| `EVIDENCE_STORAGE_BACKEND`, `EVIDENCE_BUCKET` | Optional private object storage |
| `AWS_ENDPOINT_URL_S3`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3-compatible endpoint/signing configuration |

A URI/secret declaration is not proof of successful connectivity. Confirm dependencies with readiness and representative authorized reads.

## Vercel frontend

- Project root: `frontend`.
- Install from the committed lockfile.
- Build: `npm run build`; output: `dist`.
- `VITE_API_BASE_URL`: actual API origin, currently the Render origin above.
- `VITE_DEMO_MODE=true`: explicitly enables the read-only synthetic entry route. Set false for a build that must not offer it.

The build reads shared contracts, the canonical intelligence artifact, and the synthetic graph outside `frontend/`. A deployment checkout must retain those repository paths. The build derives ten initial worklist rows and validates their synthetic profile/seed.

[vercel.json](../frontend/vercel.json) controls SPA fallback and cache headers. Module preloads and [verify-build.mjs](../frontend/scripts/verify-build.mjs) validate asset closure. A one-reload-per-build asset recovery path handles a racing deployment; it is not a general backend refresh mechanism.

## Entry and recovery behavior

| Flow | Behavior |
| --- | --- |
| Local demo role | Opens `/demo` without a JWT, using read-only synthetic metrics/worklist |
| Background demo login | Four bounded attempts; 120-second overall deadline including backoff |
| Regular credential form | Separate server-login flow with existing per-request deadline and bounded retries |
| Live read recovery | Four attempts for selected transient errors, 2/40/70-second backoff, normally 20-second read deadlines |
| Exhausted reads | Retain labelled snapshot/last confirmed values; explicit retry and bounded healthy-read catch-up |
| Mutations | Never automatically replayed by the read-recovery policy |
| Exit/logout | Cancel pending demo connection work and invalidate obsolete session responses |

The local snapshot has **Demo snapshot · Connecting**, **Live data connected**, or **Offline demo** states. It is not inserted into successful API cache entries. A live empty response is different from a failed request.

## Startup lifecycle

1. Import application modules.
2. Validate configuration and construct the repository.
3. Connect/validate PostgreSQL schema and hydrate indexes when configured.
4. Prepare canonical reads and integrity/audit services.
5. Expose HTTP and start the lifespan-owned graph task in background mode.
6. Connect Neo4j, validate schema, synchronize, and read the durable projection before opening graph gates.

Optional PDF imports and S3 client creation happen at first feature use. Mandatory repository/persistence/integrity work remains synchronous.

Background graph connection delays are **0/2/4/30/60 seconds**, at most five attempts. They do not block the already-running HTTP service. Schema/sync/read are not blindly replayed after arbitrary failures. Exhaustion keeps graph-specific routes unavailable; a permanently invalid hostname needs configuration correction, not infinite retries.

## Monitoring

| Probe | Meaning |
| --- | --- |
| [`/health`](https://nexus-4djk.onrender.com/health) | Process liveness; can succeed while dependencies are degraded |
| [`/ready`](https://nexus-4djk.onrender.com/ready) | Storage and configured graph policy; reports connection versus operational projection |
| Representative authenticated read | Confirms the actual user-facing path, not just container liveness |

Monitor the Render API separately from the Vercel URL. A static-page monitor cannot establish that the API is awake. No external monitor configuration is changed by this repository.

Readiness exposes stage timings and sanitized failure types. `factory_to_http_ready_ms` excludes module imports and platform scheduling; do not compare it directly with a launch-to-ready or browser wake-up stopwatch.

On October 28 the logged Neo4j hostname returned NXDOMAIN locally. Confirm the active Aura URI and database privately; do not guess a replacement or print credentials. The latest observed rollout had available PostgreSQL and degraded graph readiness. These observations are historical, not a promise of current uptime.

## Private evidence infrastructure

`neon.ts` declares a private bucket and an optional standalone hello function. Root `package.json`/`package-lock.json` support that configuration. `hello.ts` is not the NEXUS Python API. Preserve these files unless intentionally changing infrastructure.

The S3-compatible client uses private content-addressed keys, repository metadata, and checked downloads. No public object URL is required. Never place secrets or project credentials in this guide.

## Local containers and deployment boundaries

[Compose](../docker-compose.yml) is local-only, uses private password inputs, and binds services to loopback. It is useful for database services.

The full frontend container path needs build-context validation for the current shared/canonical snapshot inputs; native development is the verified setup path. Do not advertise Docker, Kubernetes, AKS, or sovereign production hosting as independently validated deployments.

The active [CI workflow](../.github/workflows/ci.yml) runs verification. The former Catalyst/CaseClock tag-release placeholder is [archived](archive/2026-10-28-legacy-catalyst-release.yml), not an active deployment pipeline.

## Release verification

Before describing a release as deployed:

1. Verify the intended commit/branch and push normally.
2. Confirm the served frontend build/commit, not merely a 200 page response.
3. Inspect Render readiness and current startup diagnostics.
4. Exercise an authorized core read and a graph-specific route separately.
5. Record browser and actual idle-cold results separately from component tests, warm HTTP requests, or injected failures.
6. Keep secrets and temporary logs out of the repository.

No deployment access, browser availability, or successful database recovery should be inferred from a screenshot alone.
