# Data model

> Reviewed 2026-10-28. CURRENT contracts are defined in code; examples here explain boundaries rather than invent alternate schemas.

## Sources of truth

| Layer | Source |
| --- | --- |
| Graph entity/relationship enums | [enums.py](../backend/app/core/graph/enums.py) |
| Typed graph entities | [entities.py](../backend/app/core/graph/entities.py) |
| Edges and provenance | [edges.py](../backend/app/core/graph/edges.py) |
| API/domain models | [api.py](../shared/contracts/api.py) and [api.ts](../shared/contracts/api.ts) |
| Graph-intelligence payloads | [graph_models.py](../backend/app/api/graph_models.py) |

Do not infer the complete schema from a screenshot or copy a model declaration from an archived design document.

## Graph entities — CURRENT

The model includes the core domains below, plus source and supporting entities. The old “12 types” description was incomplete: `GraphEntityType` also declares `SourceRecord`, `Officer`, `Unit`, `Court`, `Act`, `Section`, `CrimeHead`, and `CrimeSubHead`.

| Domain | Representative entity types | Interpretation |
| --- | --- | --- |
| People and investigations | Person, Case | Case participants and investigation records; participation does not establish guilt |
| Communication | Phone, Device | Identifiers and observed usage, with source attribution |
| Financial | Account, Transaction | Recorded accounts and transfers |
| Physical context | Vehicle, Location, Organization | Referenced assets, places, and organizations |
| Events and evidence | Event, IntelligenceReport, Evidence, SourceRecord | Observations, source payloads, and evidentiary lineage |
| Supporting classification | Officer, Unit, Court, Act, Section, CrimeHead, CrimeSubHead | Operational and classification context |

Entity properties differ by model. Repository artifact nodes use `id`, `entity_type`, and `properties`; API views can add display labels, case scopes, or computed summaries.

## Relationships and epistemic class

Examples include `ACCUSED_IN`, `COMMUNICATED_WITH`, `USES_PHONE`, `OWNS_ACCOUNT`, `TRANSFERRED_MONEY_TO`, `HAS_EVIDENCE`, and `RESOLVED_TO`. The enum and edge validators define allowed types/endpoints; this list is not exhaustive.

A `GraphEdge` carries source/target identifiers, edge type, provenance, optional temporal bounds, derivation class, and storage mode. It can distinguish stored records from computed relationships.

| Classification | Meaning |
| --- | --- |
| FACT | Represented directly in a source record |
| DERIVED | Computed from source-backed facts by an identified method |
| HYPOTHESIS | A proposition requiring verification; not an observed fact |

Confidence values describe a modelled association or source assessment. They must not be relabelled as guilt, criminal propensity, or judicial certainty.

## Evidence provenance — CURRENT

The implemented `EvidenceProvenance` includes:

- `source_type`, `source_id`, and optional `source_record_id`.
- `timestamp` and `extracted_fact`.
- `derivation_method` and `derivation_class`.
- Bounded `confidence` in [0, 1].

The data contract supports attribution; meaningful source linkage still depends on ingestion validation and the source record. A hash/provenance object does not prove the content is true or legally sufficient.

Source bytes, canonical source-record payloads, evidence metadata, audit-chain records, and generated PDFs have different integrity checks. Do not substitute one digest for another.

## Intelligence domain records — EXTENSION / NEW PROTOTYPE

| Contract family | Purpose | Lifecycle |
| --- | --- | --- |
| GraphSnapshotSummary, NetworkDiffResponse | Versioned graph views and structural deltas | EXTENSION |
| NetworkPulseItem | Review headline, evidence references, affected scope, and review priority | EXTENSION |
| EvidenceAssessmentItem | Pulse-embedded assessment view | EXTENSION |
| EvidenceAssessment | First-class assessable record with revision history and contextual linkage | EXTENSION |
| VerificationActionItem | Suggested verification action attached to a pulse | EXTENSION |
| VerificationTask | Persistent task with assignment, transition history, attached evidence, and decisions | EXTENSION |
| IntelligenceEvent | Typed operational occurrence with provenance and contextual links | EXTENSION |
| IntelligencePulsePacket, AffectedInvestigationRoute | Internal packet delivery and affected-case routing | EXTENSION |
| ForecastItem | Constrained prototype target/uncertainty/abstention representation | NEW PROTOTYPE |
| IdentityDriftEvent, NetworkAdaptationEvent, DigitalShadowCorroboration | Reviewable analytical/corroboration records | NEW PROTOTYPE |
| CaseDNA and associated match responses | Explainable structural similarity | NEW PROTOTYPE |

Consult shared contracts for exact fields and enums. A contract's existence does not certify a general-purpose production engine.

## Canonical synthetic artifacts and counts

| Source | Role |
| --- | --- |
| [nexus_graph.json](../artifacts/nexus_graph/nexus_graph.json) | Base generated synthetic graph; 445 nodes / 486 edges in the checked-in artifact |
| [ground_truth.json](../artifacts/nexus_graph/ground_truth.json) | Planted identities, communities, bridge, and transaction chains |
| [canonical_read_model.json](../backend/app/db/canonical_read_model.json) | Versioned intelligence snapshot, pulse examples, and KPI scope |
| [demoEntrySnapshot.json](../frontend/src/lib/demoEntrySnapshot.json) | Build-generated ten-row worklist projection and normalized source checksum |

The base graph, enriched repository, historical benchmark workloads, and deployed database need not have identical counts. For example, a deployment can contain enrichment and investigator state beyond the untouched artifact. Keep every count attached to its source and timestamp.

The canonical intelligence read model has six golden-path worklist entries; the instant-entry projection deliberately uses ten records from the larger graph artifact. These are related views with different scopes, not interchangeable “total case” counts.

## Ownership and persistence

PostgreSQL-backed mode persists application/workflow records while hydrating indexes. Neo4j is a complementary graph projection, not the credential or workflow source of truth. Private object storage holds source bytes when enabled. See [architecture](ARCHITECTURE.md).

Snapshot baseline objects are read-only frontend inputs, not successful query-cache responses or server sessions. Live API results replace their own baseline scope only after authorized reads.

## TARGET / FUTURE

Production identity-directory records, inter-agency federation, independently validated forecast calibration, and cross-system atomic delivery guarantees require additional design and verification. Do not add speculative copies of those schemas here; record accepted changes in [decisions.md](../decisions.md) and implement shared contracts first.
