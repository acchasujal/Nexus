# Catalyst Data Store Spike Plan

This document defines the validation plan for representing the unified investigation graph in Catalyst Data Store using an adjacency-list style model.

## Goal

Validate whether Catalyst Data Store can support the graph foundation with acceptable correctness and query behavior before any backend implementation is frozen.

## Validation Scope

The spike should test:

- CRUD behavior for entity tables
- Relationship storage and lookup
- Foreign key behavior or the lack of it
- Join capability across node and edge tables
- Pagination for list views
- Index behavior on graph lookup columns
- Recursive query support for multi-hop graph traversal
- Practical limitations and a fallback plan if recursion is unsupported
- Transaction support and write atomicity
- Bulk insert performance under the synthetic dataset
- Concurrent read behavior during dashboard-style access
- Export/import round-trip behavior for seeded graph data

## Test Matrix

### 1. CRUD Tests

Validate that the store can create, read, update, and delete rows for representative node types and edge records.

Test set:

- Create a Case, Person, Officer, Dependency, and ClockInstance row.
- Read them back by primary key.
- Update non-key fields in each row.
- Delete a row and confirm the expected deletion semantics.

Expected outputs:

- Newly created rows are immediately retrievable.
- Updates are visible on subsequent reads.
- Deletes either remove the row or are blocked depending on the chosen integrity policy.

Additional checks:

- Confirm that a repeated create with the same primary key is rejected or cleanly upserts according to the chosen datastore semantics.
- Confirm that write operations are atomic at the row level so partially written graph records do not appear.

### 2. Foreign Key Behavior

Validate whether Catalyst enforces referential integrity between node tables and edge rows.

Test set:

- Attempt to create an edge that points to a missing source or target entity.
- Attempt to delete a parent entity that still has dependent edge rows.

Expected outputs:

- If foreign keys are supported, invalid references should be rejected.
- If foreign keys are not supported, the application layer must detect broken references.

Possible limitation:

- Catalyst may not expose full relational foreign key enforcement for graph-like use cases.

### 3. Join Capability

Validate joins between Case, Person, Officer, Dependency, and edge tables.

Test set:

- Join Case to its Person roles.
- Join Case to its Dependency records.
- Join Case to its ClockInstance rows.
- Join Officer to Unit.

Expected outputs:

- Joined results should return the correct related rows without duplicating unrelated records.
- Left joins should preserve cases with no optional related data.

### 4. Pagination

Validate that large result sets can be paginated predictably.

Test set:

- Page through 500 Case rows.
- Page through 900 Person rows.
- Confirm stable ordering with repeated requests.

Expected outputs:

- Page size limits are honored.
- Next-page access returns the following slice without overlap or gaps.
- Ordering remains stable across repeated reads.

Additional checks:

- Confirm pagination remains stable after inserts into earlier pages.
- Confirm cursor or offset behavior does not duplicate or skip rows when the result set changes.

### 5. Index Testing

Validate whether indexing the graph lookup columns improves fetch performance.

Recommended indexed columns:

- case identifiers
- person identifiers
- edge source identifiers
- edge target identifiers
- relationship type
- station / district lookup columns
- dependency status
- clock status

Expected outputs:

- Point lookups should remain fast under the synthetic dataset.
- Edge lookups by source case should scale better with indexing than without it.

Possible limitation:

- Index support may exist only for simple scalar columns, not for graph-specific query patterns.

Additional validation:

- Compare query latency before and after indexes on the same synthetic dataset.
- Validate that the edge lookup columns used by traversal queries are the actual ones that benefit from the index.

### 6. Recursive Query Testing

Validate whether Catalyst can express multi-hop traversal in the data layer.

Test set:

- Two-hop person-to-person traversal through shared case membership.
- Multi-step case-to-case or person-to-case traversal through edge chaining.
- A small chain of connected records that proves whether recursion is supported natively.

Expected outputs:

- If recursion is supported, the query should return the full reachable path or the expected downstream set.
- If recursion is not supported, the test should confirm that only one-hop joins are available.

Possible limitation:

- Recursive SQL or graph-style traversal may not be available in Catalyst Data Store.

Additional validation:

- Confirm whether recursion depth limits exist.
- Confirm whether recursive reads remain stable under concurrent access.

### 7. Expected Outputs

The spike should produce a short evidence report containing:

- Whether CRUD passed
- Whether referential integrity is enforced
- Whether joins are practical for the graph model
- Whether pagination is reliable
- Whether indexes help materially
- Whether recursive traversal is natively supported
- Whether transactions behave atomically for graph writes
- Whether bulk inserts complete within a usable time window for seed generation
- Whether concurrent reads remain stable while writes are in progress
- Whether export/import preserves node and edge identity

## If Recursive SQL Is Unsupported

Use the following workaround strategy:

1. Store nodes in entity tables and edges in a dedicated adjacency table.
2. Resolve one-hop relationships with standard joins.
3. Resolve multi-hop relationships in application code or by precomputing closure data.
4. Materialize frequently used derived relationships such as co-accused links only if the downstream use case requires it.
5. Keep derived outputs clearly separated from canonical stored edges.

Recommended workaround choice:

- Prefer application-layer traversal for low-latency demo flows.
- Prefer a closure table or precomputed path cache only if repeated multi-hop queries become a bottleneck.

Additional fallback notes:

- If transaction support is weak, batch writes should be decomposed into idempotent phases with clear retry boundaries.
- If bulk inserts are slow, seed data should be split into smaller logical batches by entity type and edge type.
- If export/import is lossy, keep a canonical source-of-truth export outside Catalyst for regeneration.

## Acceptance Criteria

- The spike produces a clear yes/no answer for whether Catalyst can host the graph model directly.
- The report identifies any unsupported capability before implementation starts.
- A fallback adjacency strategy is documented if native recursion is unavailable.

## Risks To Watch

- Joins may work but still be too slow for graph-heavy screens.
- Recursive support may exist in theory but not be practical at the expected dataset size.
- Edge integrity may need to be enforced outside the datastore.
- Pagination semantics may differ between simple tables and relationship tables.
