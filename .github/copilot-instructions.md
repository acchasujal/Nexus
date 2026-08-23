# NEXUS GitHub Copilot Instructions

## Project Context
- **System:** NEXUS (Evidence-Grounded Criminal Network Intelligence System)
- **Competition:** SIH 2026 Problem Statement 26189
- **Domain:** Law Enforcement & Criminal Network Analytics (CCTNS/ICJS/CDR/Banking)

## Key References
- Primary Specification: `NEXUS.md`
- Active Task Board: `PROGRESS.md`
- AI Rules & Constraints: `AGENTS.md`
- System Architecture: `docs/ARCHITECTURE.md`
- Graph Ontology & Data Model: `docs/DATA_MODEL.md`

## Development Constraints
- Use Python 3.11+ (FastAPI, Pydantic v2, NetworkX) for backend services.
- Use React 18 (TypeScript, Vite, Tailwind CSS, React Flow) for frontend interfaces.
- Strictly adhere to deterministic analysis first (no autonomous guilt scoring or recidivism predictions).
- Bind all graph relationship edges to `EvidenceProvenance` records.
- Run `pytest` and `npm test` before committing any changes.
