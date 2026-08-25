# ADR-001: Hybrid In-Memory Graph and Polyglot Persistence Architecture

## Status
**Accepted & Implemented**

## Context
Criminal intelligence analysis requires sub-second multi-hop traversals, centrality calculations, and community clustering over complex, multi-relational networks. Traditional relational SQL databases suffer severe performance degradation during recursive multi-hop joins. Pure graph databases like Neo4j excel at deep traversals but introduce network latency when calculating global topological properties (e.g. betweenness centrality across thousands of nodes) during interactive UI sessions.

## Decision
NEXUS adopts a **hybrid polyglot persistence architecture**:
1. **In-Memory `GraphStore`:** Implements dual adjacency lists (`adj` and `radj`) in Python memory with hash indexing by edge type and entity type. Delivers sub-millisecond 1-hop, 2-hop, and 3-hop BFS expansions (< 0.025 ms).
2. **Neo4j 5 Community / Cypher:** Serves as the persistent graph database for Cypher queries, graph visualization projections, and complex pattern matching.
3. **PostgreSQL 16:** Stores structured relational case registries, user authentication tables, and immutable audit logs.

## Consequences
- **Positive:** Sub-second latency SLAs for all interactive graph explorer features; zero database network overhead for real-time BFS expansions.
- **Trade-off:** Graph must be serialized and indexed in memory upon application startup (measured at 6.05 ms for 445 nodes / 530 edges).

## Entity Resolution & Cross-Case Identity Semantics
Entity resolution operates across all ingested source records globally. Case identifiers serve exclusively as contextual provenance metadata rather than canonical identity boundaries. An entity can appear legitimately across multiple distinct cases (e.g. accused in CASE-141 and CASE-207), and candidate generation compares records across case boundaries without case-scoped restriction.

