# Shared contract history

The current contract definitions are [api.py](api.py) and [api.ts](api.ts). They are maintained together; there is no claim that this folder is a separately published, versioned package.

## Current contract coverage

- Investigation summaries/details, graph nodes/edges and evidence provenance.
- Entity resolution candidates and review decisions.
- Documents, ingestion candidates and document text.
- Copilot queries, responses and citations.
- Snapshots, differences, pulses and evidence assessments.
- Verification tasks, intelligence routing and related analytical read models.

See the [API guide](../../docs/API.md) for implemented route families and the [data model](../../docs/DATA_MODEL.md) for domain boundaries. Add future changes here with the affected contract and compatibility implications.

## Historical initial baseline

The original “1.0.0” note described the initial graph, resolution, copilot and investigation contract families. Some symbol names in that note no longer exist; use the definitions above rather than treating the old list as a current interface specification. Git history retains the original note.
