# Documentation Migration Rules

The current repository already has canonical documentation. Do not create another layer of competing markdown files.

## Canonical files

Keep:
- `README.md`
- `progress.md`
- `decisions.md`
- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/DATA_MODEL.md`
- `docs/INTELLIGENCE_PIPELINE.md`
- `docs/SECURITY.md`
- `docs/BENCHMARKS.md`
- `docs/DEMO.md`
- `docs/DEPLOYMENT.md`
- `docs/DEVELOPMENT.md`

Archive obsolete/historical reports instead of leaving contradictory active docs.

## Transformation requirements

### README
Must explain:
- the current product
- the target differentiator
- current implementation status
- quick-start
- test status
- prototype-vs-vision boundary

### ARCHITECTURE
Must be updated to show:
- temporal snapshots
- network diff
- pulse
- early warning
- evidence assessment
- verification
- intelligence pulse
- trust fabric
- feedback loop

### DATA_MODEL
Must include the target delta objects defined in `06_DATA_MODEL_DELTA.md`.

### API
Must describe actual implemented endpoints only.
Future endpoint designs belong in clearly marked target/roadmap sections.

### INTELLIGENCE_PIPELINE
Must evolve from the 7-stage pipeline to:
source → normalize → resolve → graph → change → warning → evidence → verify → propagate → investigator → audit/update.

### BENCHMARKS
Must separate:
- current measured results
- target metrics
- synthetic-only claims
- field/real-world claims

### SECURITY
Must cover proactive signals, SOCMINT governance, routing authorization and future trust mechanisms.

### DEMO
Must transition from:
ER → centrality → timeline → Copilot

to:
Network Change → Pulse → Evidence Assessment → Early Warning/Abstention → Verification → Intelligence Pulse → Integrity → Copilot explanation → Human decision.

### progress.md
Record implementation status only.

### decisions.md
Record accepted architectural decisions only.

## Documentation anti-bloat rule

Never create:
- `FINAL_ARCHITECTURE_v2.md`
- `NEW_ROADMAP.md`
- `LATEST_STATUS.md`
- `UPDATED_API.md`
- duplicated feature reports

Update the canonical file or archive an obsolete one.
