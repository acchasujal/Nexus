# NEXUS contributor context

Read [repository governance](../AGENTS.md), [current status](../progress.md) and [decisions](../decisions.md) before editing. Actual code and tests take precedence over documentation; archived plans are historical references, not active instructions.

- Backend: Python 3.11+, FastAPI, Pydantic v2 and deterministic graph algorithms.
- Frontend: React 19, TypeScript, Vite, TanStack Query and React Flow.
- Use synthetic data only. Preserve relationship provenance and explicit abstention.
- Never introduce guilt, criminality or recidivism scoring.
- Local demo roles are not server authorization. Do not weaken backend checks.
- Reuse existing services and components; make focused changes and preserve unrelated edits.
- Keep active documentation in the canonical [docs](../docs/) set, progress in the root status file and architectural decisions in the root decision log.
- Run the verification commands in [CONTRIBUTING](../CONTRIBUTING.md). Report existing failures honestly; do not disable tests or invent green counts.
