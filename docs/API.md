# API reference

> Reviewed 2026-10-28. CURRENT route inventory with prototype scope noted. Router code and generated OpenAPI take precedence over prose.

## Contract sources

- [Core routes](../backend/app/api/core_routes.py): investigations, evidence, documents, resolution, copilot, export, and audit.
- [NEXUS routes](../backend/app/api/nexus_routes.py): snapshots, pulses, analytical prototypes, and workflow extensions.
- [Graph routes](../backend/app/api/graph_routes.py): graph-intelligence projections.
- [System routes](../backend/app/api/system_routes.py): dependency readiness and telemetry.
- [Python contracts](../shared/contracts/api.py), [TypeScript contracts](../shared/contracts/api.ts), and [graph API models](../backend/app/api/graph_models.py).

Run the local server and open `http://localhost:8000/docs` or `/openapi.json` for the complete parameter, validation, and response schemas. Core and NEXUS routers are mounted at root and `/api/v1`; the graph router is mounted at `/api/v1/graph`. Chat also has an `/api/chat` route.

## Identity and availability

`POST /api/v1/auth/login` accepts `AuthLoginRequest` and returns `AuthTokenResponse`. The current handler resolves predefined demo identities and issues a signed token; it does not implement a production password directory. Demo verifier shortcuts remain in the backend. See [security](SECURITY.md).

The frontend's local `/demo` is a browser route, not an API login or an authorization bypass. Before server-session establishment it only shows bundled synthetic records.

Ordinary JSON responses can return validation/access errors. Live graph operations return 503 while the configured projection is unavailable. A successful health response or server login does not imply that every dataset/graph request will succeed.

## Implemented endpoint groups

Paths below include the preferred `/api/v1` prefix. This is a navigation index, not a replacement for OpenAPI.

### Investigation, entity, and evidence foundation — CURRENT

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Establish a server-issued demo session |
| GET | `/api/v1/investigations` | Worklist; supports district/category/status filters |
| GET | `/api/v1/investigations/{case_id}` | Investigation detail |
| GET | `/api/v1/network/cases/{case_id}` | Case-centred network expansion |
| GET | `/api/v1/entities` | Entity list/search |
| GET | `/api/v1/entities/{entity_id}` | Entity profile |
| GET | `/api/v1/entities/{entity_id}/network` | Entity-centred network |
| POST | `/api/v1/entity-resolution/resolve` | Explainable candidate matching |
| GET | `/api/v1/communities` | Community analysis |
| GET | `/api/v1/influence/bridges` | Bridge-node analysis |
| GET | `/api/v1/influence/rankings` | Centrality ranking |
| GET | `/api/v1/timeline` | Investigation timeline |
| GET | `/api/v1/evidence` | Evidence list |
| GET | `/api/v1/evidence/{evidence_id}` | Evidence record |
| POST | `/api/v1/evidence/verify` | Evidence integrity verification |
| POST | `/api/v1/copilot/query` | Citation-bearing investigative response |
| GET | `/api/v1/audit` | Audit records subject to policy |

Legacy aliases such as `/worklist` and `/cases/{case_id}` are marked deprecated in the core router. New clients should use the preferred routes.

### Ingestion, documents, and candidate decisions — CURRENT / EXTENSION

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/ingest` | Core ingestion batch |
| POST | `/api/v1/nexus/ingest` | NEXUS ingestion flow |
| POST | `/api/v1/documents` | Upload a document |
| GET | `/api/v1/documents/{document_id}` | Document metadata |
| GET | `/api/v1/documents/{document_id}/download` | Authorized source-byte download |
| GET | `/api/v1/documents/{document_id}/text` | Extracted text |
| POST | `/api/v1/documents/{document_id}/extract` | Candidate extraction |
| GET | `/api/v1/documents/{document_id}/candidates` | Review extracted candidates |
| POST | `/api/v1/candidates/{candidate_id}/accept-entity` | Link a reviewed candidate to an entity |
| POST | `/api/v1/candidates/{candidate_id}/accept-new` | Accept a reviewed new entity |
| GET | `/api/v1/nexus/resolution/candidates` | Resolution review queue |
| POST | `/api/v1/nexus/resolution/{candidate_id}/decision` | Record CONFIRM/REJECT/DEFER-style decisions as defined by the request contract |

Use the actual request enums from shared contracts; UI wording and older plans are not payload definitions. Upload endpoints use multipart form data where declared.

### Snapshots and intelligence — EXTENSION

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/v1/nexus/network` | Snapshot-aware canonical network |
| GET | `/api/v1/nexus/network/diff` | Existing snapshot-diff response |
| GET | `/api/v1/nexus/path` | Evidence-linked pathfinding |
| GET | `/api/v1/nexus/relationships/{rel_id}/evidence` | Relationship evidence |
| GET | `/api/v1/nexus/sources/{source_id}` | Source record |
| POST | `/api/v1/nexus/sources/{source_id}/verify` | Recompute source integrity |
| GET / POST | `/api/v1/nexus/snapshots` | List/create snapshots |
| GET | `/api/v1/nexus/diff` | Proactive network diff |
| GET | `/api/v1/nexus/pulses` | Filtered review pulses |
| GET | `/api/v1/nexus/intelligence/bootstrap` | Dashboard KPIs derived from the current pulse/assessment scope |
| GET | `/api/v1/nexus/leads` | Lead queue |
| POST | `/api/v1/nexus/leads/{lead_id}/decision` | Lead review |
| POST | `/api/v1/nexus/copilot/query` | NEXUS copilot flow |

Forecast and verification recommendation objects can be attached to pulse responses. They are prototype outputs, not a separately deployed general forecasting API.

### Analytical radars — NEW PROTOTYPE

GET collections under:

- `/api/v1/nexus/intelligence/identity-drift`
- `/api/v1/nexus/intelligence/network-adaptation`
- `/api/v1/nexus/intelligence/digital-shadow`
- `/api/v1/nexus/intelligence/case-dna/{case_id}`

The first three also expose summary and decision operations as declared in the router. Hotspot, repeat-case, and combined intelligence views live under `/nexus/intelligence/`. These do not establish a real-world identity or guilt finding.

### Workflow and integrity extensions

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/nexus/intelligence/pulses/dispatch` | Create an internal intelligence packet |
| GET | `/api/v1/nexus/intelligence/pulses/inbox` | Authorized packet inbox |
| POST | `/api/v1/nexus/intelligence/pulses/{packet_id}/acknowledge` | Packet acknowledgement |
| POST | `/api/v1/nexus/routing/evaluate` | Evaluate affected investigations |
| GET | `/api/v1/nexus/routing/inbox` | Affected-investigation inbox |
| GET / POST | `/api/v1/nexus/intelligence/events` | Intelligence event records |
| GET / POST | `/api/v1/nexus/verification/tasks` | Persistent verification tasks |
| GET / POST | `/api/v1/nexus/evidence/assessments` | First-class evidence assessments |
| GET | `/api/v1/nexus/propagation/{decision_id}` | Closed-loop propagation result |
| POST | `/api/v1/nexus/propagation/retry/{decision_id}` | Explicit propagation recovery |
| POST | `/api/v1/nexus/evidence/dossier` | Generate a dossier |
| GET | `/api/v1/nexus/evidence/dossier/{dossier_id}/download` | Authorized PDF download |
| POST | `/api/v1/nexus/evidence/dossier/{dossier_id}/verify` | Dossier integrity check |

Task assignment/transitions/evidence/decisions and assessment revisions are explicit mutations. Do not automatically replay them after a network error.

## Graph projection API — CURRENT

The `/api/v1/graph` family includes case/person networks, co-accused, paths, similarity/compare, dashboard aggregates, hotspots, repeat-case profiles, components, centrality, and stats. These operate on the graph-intelligence repository and must not be conflated with canonical snapshot reads.

## Health and readiness

| Endpoint | Meaning |
| --- | --- |
| `GET /health` | Process liveness; not dependency health |
| `GET /ready` | Storage and configured graph failure policy; 200 ready/degraded or 503 not ready |
| `GET /api/v1/system/status` | Application telemetry; not a replacement for readiness |

Readiness includes storage availability, graph connection/operational distinction, graph initialization stage/attempts, and startup timings. Diagnostics omit credentials and raw exception messages.

## Not implemented as production integrations

External police-system connectors, production identity federation, cross-agency ledger consensus, general calibrated forecasting, and arbitrary real-time social-media collection are TARGET / FUTURE or excluded scope. Older proposed URLs in the [archive](archive/README.md) are not current API contracts.
