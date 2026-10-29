# Implementation status

Last implementation review: **2026-10-30**. This is the current status register; detailed older entries are preserved in the [historical progress log](docs/archive/2026-10-28-progress-history.md). Code and tests take precedence over narrative status.

## Investigator entry restored — 2026-10-30

**CURRENT:** officer role selection and credential submission both await server login, then open the original `/intelligence` workspace or a safe preserved internal destination. The existing AppShell, navigation, protected pages and independent data queries remain in place. The standalone local demo page and its feature flag were removed. `/demo` remains only as a compatibility redirect through protected routing.

Stored readable, unexpired sessions survive refresh. Logout, expiry, server 401 and the backend verifier's explicit invalid-token 403 invalidate the session; ordinary permission-denied 403 responses do not. Late unauthorized responses for an older token cannot invalidate a newer stored session. Backend authentication/authorization code is unchanged.

Verification:

- Actual route-tree/session coverage: **30 new tests passed**, including pending/failed panel APIs, all officer roles, deep links, refresh, logout/history, expiry, unknown routes and redirect safety.
- Full frontend: **175 passed, 47 failed**, 222 tests, 43.84 s. An isolated checkout of pre-change `d9fbd65` reproduced **161 passed, 47 failed** (208 tests); failure headers match with no additions. Obsolete standalone-demo tests were replaced with workspace-routing tests. Two existing fixtures now use readable synthetic session payloads rather than arbitrary strings; assertions are unchanged.
- Frontend ESLint passed with 0 errors and 86 existing warnings. Production build passed TypeScript, Vite and integrity verification (26 manifest entries, 25 preloaded modules). The full-suite quality gate remains incomplete because the baseline failures remain open.
- No backend code changed. Browser paint timing and deployed rollout were not verified for this change.

Remaining `/demo` references are intentional: the compatibility route, return-path loop protection, routing tests and current/historical documentation. `/nexus/demo/reset` API routes, mocks, scripts and backend tests are unrelated synthetic reset functionality and remain unchanged. Shared `demoBaseline`/`demoEntrySnapshot` artifacts and their generator/imports remain used by the authenticated workspace. `VITE_DEMO_MODE` survives only in retired-flag documentation and a regression test proving it no longer changes routing. No normal navigation link targets the old page.

## Current scope

| Area | Lifecycle | Verified scope / boundary |
| --- | --- | --- |
| Investigative graph, entity resolution, copilot, audit and dossiers | CURRENT | Implemented synthetic-data services; not production accreditation |
| Snapshot diff, review pulses, evidence and verification workflows | EXTENSION | Deterministic findings with evidence-linked review |
| Identity drift, adaptation, digital shadow and Case DNA | NEW PROTOTYPE | Implemented prototype slices, not field-validated predictions |
| Authenticated investigator entry and data recovery | CURRENT / EXTENSION | Server-confirmed session; existing shell and independently recovering panels |
| Government identity integration, real-record deployment and calibrated forecasting | TARGET / FUTURE | Not implemented or certified |
| Guilt prediction, raw sensitive records on public chains | REJECTED | Outside the product's permitted scope |

## Previous verification — 2026-10-28

Full baseline suites were run on 2026-10-28 before this documentation cleanup; application source was unchanged by the cleanup.

| Check | Actual result |
| --- | --- |
| Backend pytest | **921 passed, 2 skipped**, 3 warnings; 133.73 s |
| Frontend Vitest | **161 passed, 47 failed**, 208 tests across 33 files; 47.89 s |
| Ruff: backend, shared, tests | Passed |
| Seeded entity-resolution evaluation | Passed: 2 true positives, 0 false positives, 0 false negatives; 100% precision/recall on this fixture |
| Frontend production build | Passed: TypeScript, Vite and build-integrity verification |
| Frontend ESLint | Passed with 86 existing warnings, 0 errors |
| Documentation links | 206 local links checked across 17 active/index documents; no missing targets |
| GitHub workflow/issue YAML | Syntax parsed successfully |

The 47 frontend failures reproduce the known baseline failure count from before this documentation task. This is **not an all-green repository**. They remain unresolved; this cleanup does not change assertions, disable tests or weaken the quality gate. The required end state remains all suites passing. Test counts are observations, not fixed acceptance thresholds.

## Recent implementation

- `0b4708e`: explicit synthetic local demo entry, generated snapshot, bounded background authentication/live-read recovery and startup import/graph recovery changes.
- `0b0ef24`: rollout evidence and operational documentation.
- 2026-10-28 documentation cleanup: rebuilt the README and canonical guides, replaced the misnamed project report with a formal report, consolidated current status/decisions, repaired repository templates and portable links, and archived obsolete material.

The earlier local-demo entry has been superseded by the authenticated workspace flow above. Server authentication is still the backend's demo identity implementation, not a production credential directory. See [security](docs/SECURITY.md).

## Deployment evidence and outstanding work

Earlier rollout checks found the public Vercel bundle contained the demo flow and the Render API responded to health/readiness requests. These were public artifact/API checks, **not a complete deployed browser acceptance run**.

The observed Neo4j hostname returned DNS failure and graph readiness was degraded. That observation is dated; it is not a claim about continuous present uptime. PostgreSQL-backed core reads and graph-specific readiness must be checked separately. See [deployment](docs/DEPLOYMENT.md).

Open work:

- Resolve the existing frontend failures without relaxing assertions.
- Verify fresh-browser delayed-backend timing and the full hosted judge journey.
- Correct and reverify deployed Neo4j DNS/configuration without exposing credentials.
- Validate the full frontend Docker build context before recommending it.
- Replace demo authentication before any real-data use.

## Documentation maintenance

Use the [README](README.md) for the entry point, [project report](docs/PROJECT_REPORT.md) for judge context, [decisions](decisions.md) for accepted architecture, and the [canonical guides](docs/) for technical detail. Historical plans and instructions are [archived](docs/archive/README.md), not active work orders. No runtime behavior was changed during this documentation cleanup.
