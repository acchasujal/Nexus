# Contributing to NEXUS

NEXUS is a synthetic-data investigative intelligence prototype for SIH 2026 PS 26189. Start with the [README](README.md), [developer guide](docs/DEVELOPMENT.md), and [agent governance](AGENTS.md).

## Before changing code

- Inspect the implementation and tests before relying on older plans.
- Reuse graph algorithms, services, and frontend components.
- Preserve shared Python/TypeScript contracts and evidence provenance.
- Keep deterministic analysis separate from generative explanation.
- Do not introduce guilt/criminality scoring, real citizen PII, or public-ledger case data.
- Preserve unrelated working-tree changes. Keep credentials and generated logs out of commits.

## Verification

From the repository root:

```sh
python -m ruff check backend/ shared/ tests/
python -m pytest
python scripts/evaluate_ground_truth.py
npm --prefix frontend run lint
npm --prefix frontend run test:run
npm --prefix frontend run build
```

Use focused tests while developing; report the full checks required by [AGENTS.md](AGENTS.md) before declaring completion. State baseline failures, skipped integration requirements, and platform blockers explicitly. Never disable tests or claim an unexecuted check passed.

The latest dated verification is in [progress.md](progress.md). Historical counts are not fixed contribution requirements.

## Documentation

| Change | Update |
| --- | --- |
| API payload/route | Shared contracts and [API guide](docs/API.md) |
| Graph/domain model | [Data model](docs/DATA_MODEL.md) and relevant tests |
| Architecture or security decision | [decisions.md](decisions.md) and the relevant canonical guide |
| Setup/deployment | Environment examples and [development](docs/DEVELOPMENT.md)/[deployment](docs/DEPLOYMENT.md) |
| Implementation or verification status | [progress.md](progress.md) |

Use CURRENT, EXTENSION, NEW PROTOTYPE, TARGET / FUTURE, or REJECTED to qualify capability claims. Keep historical material in the [archive](docs/archive/README.md); do not create competing task boards or decision logs.

## Pull requests and commits

Describe the problem, resulting behavior, and validation evidence. Include a concrete before/after example for behavioral changes. Explain remaining limitations.

Use focused commit messages such as `feat:`, `fix:`, `test:`, `docs:`, `perf:`, or `refactor:`. Do not mix unrelated formatting or generated artifacts into a functional change.

The active [CI workflow](.github/workflows/ci.yml) runs backend lint/tests/ground truth and frontend lint/tests/build. It does not deploy to Catalyst or certify production readiness.

## Security and licensing

Use synthetic reproductions when reporting defects. Never publish credentials, real case records, or citizen identifiers in issues. See [SECURITY.md](docs/SECURITY.md) for the prototype's authentication and deployment limits.

No repository license has been declared. Public visibility alone does not grant a license; obtain maintainer permission before redistribution or reuse that requires it.
