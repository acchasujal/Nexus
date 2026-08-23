# Migration Plan

This document explains how the graph foundation can later map into Catalyst Data Store using an adjacency-list model.

It does not define SQL, stored procedures, or implementation code.

## Mapping Strategy

The graph should be represented as a set of entity tables plus one edge table.

### Naming Conventions

- Use lowercase `snake_case` for table and column names.
- Prefer singular entity table names with a stable `graph_` prefix, such as `graph_case` and `graph_person`.
- Keep edge storage in a dedicated `graph_edge` table so relationship semantics stay centralized.

### Identifier Conventions

- Use UUID primary keys for every entity table.
- Preserve the same UUID shape across all graph nodes so repeat entities can be reused safely in synthetic and future real data.
- Use stable identifiers for edges only when an edge must be directly addressable; otherwise edge rows can be keyed by their own UUID.

### Foreign Key Strategy

- Prefer real foreign keys where the datastore supports them.
- If Catalyst Data Store cannot enforce foreign keys for edge rows, validate references in the application layer before write operations.
- For adjacency rows, reference source and target entity ids explicitly and keep source/target entity types alongside them for clarity.

### Entity Tables

Each entity becomes its own table so that the model stays readable and so each node type can evolve independently.

Proposed entity responsibilities:

- Case table: canonical investigation record and primary graph anchor.
- Person table: one row per synthetic or real-world identity.
- Officer table: investigation and supervisory personnel.
- Unit table: station, subdivision, district, or higher unit structure.
- Court table: judicial context.
- Location table: incident and jurisdiction geography.
- Act table: legal statute reference.
- Section table: section-level legal reference.
- CrimeHead table: top-level offence classification.
- CrimeSubHead table: detailed offence classification.
- Evidence table: attached evidentiary items.
- Dependency table: named blockers that delay filing.
- ClockInstance table: statutory deadline instances.
- EscalationEvent table: audit record of threshold-triggered escalation.
- ConversationLog table: audit record of grounded query sessions.

### Edge Table

One adjacency table should store all relationships.

Edge table responsibilities:

- source entity type
- source entity id
- relationship type
- target entity type
- target entity id
- storage mode
- created_at and updated_at timestamps if needed for auditability

Recommended structure notes:

- Keep the relationship type column aligned with the graph enum names.
- Keep source and target types explicit so the same adjacency table can store all node combinations without ambiguity.
- Add a version or schema tag only if future migrations need to coexist with older edge formats.
- Make the edge table the only canonical place for relationship storage; derived relationships should remain separate from stored facts.

This keeps the graph uniform even as new entity types are added later.

## Why This Model Works

- It matches the single unified investigation graph principle.
- It keeps node data normalized while still allowing flexible cross-entity traversal.
- It avoids hard-coding graph semantics into any one entity table.
- It makes derived relationships easy to keep separate from stored facts.

## Table Responsibility Notes

### Case

Case should remain the authoritative anchor for every downstream investigation view.

### Person

Person should carry identity-level data only. Role should be represented by edges, not by separate subtype tables.

### Officer and Unit

These tables should support rank-aware routing and organizational rollups.

### Act, Section, CrimeHead, CrimeSubHead

These tables should support legal classification, pattern analysis, and clock mapping.

### Evidence and Dependency

These tables should support investigative status, blocking reasons, and workload visibility.

### ClockInstance and EscalationEvent

These tables should support deterministic deadline tracking and auditable escalation outcomes.

### ConversationLog

This table should preserve grounded interaction history for audit, explainability, and export.

## Derived Relationship Handling

Derived relationships should not be treated as primary stored facts in the initial migration.

- CO_ACCUSED_WITH should be derived from Person-to-Case participation.
- LINKED_TO should only appear when a verifiable shared attribute exists.

If future performance work requires materialization, derived relationships can later be cached separately, but they should never replace the canonical edge table.

## Future Evolution Path

If Catalyst Data Store proves adequate, the model can remain mostly unchanged and only the query layer needs to mature.

If Catalyst Data Store lacks recursive traversal, the system can still keep the same model by moving multi-hop traversal into application logic or precomputed relationship caches.

If later features require richer metadata, add columns to the relevant entity tables rather than creating a second graph system.

If relationship fan-out or traversal depth grows significantly, add a materialized helper layer on top of the same adjacency model instead of replacing the graph schema.

## Migration Principles

1. Keep one canonical node per entity instance.
2. Keep one canonical adjacency table for all relationships.
3. Store derived relationships separately from canonical edges.
4. Preserve stable identifiers for repeat synthetic entities.
5. Avoid schema drift that would split the unified graph into parallel models.
