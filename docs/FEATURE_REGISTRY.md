# FEATURE_REGISTRY.md

Every planned feature, described by intent (purpose, users, workflow, acceptance criteria) — not implementation. Cross-reference `ARCHITECTURE.md` for how these map onto the unified graph, and `TASK.md` for build status.

Status legend: **MVP** (must exist for hackathon submission) / **Finals** (post-shortlist refinement) / **Roadmap** (explicitly not built, stated aspiration only).

---

## Graph Infrastructure

- **Graph Repository**: Bridges persistent database models with the in-memory graph. Exposes node and relation queries in [graph_repository.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/repositories/graph_repository.py).
- **Graph Loader**: Constructs the unified in-memory graph representation from flat node and edge records in [graph_loader.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py).
- **Graph Validation**: Structural and referential checks (missing endpoints, orphans, empty/duplicate keys, self-loops) to guarantee graph integrity before analytical computation inside [GraphLoader.validate_graph](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py#L68-L170).
- **GraphStore**: Memory-efficient unified property graph data structure using fast O(1) indices for nodes and adjacency edge lists in [GraphStore](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/utils.py#L58-L76).

---

## Graph Analytics

- **Similarity Search**: Retrieves the top-k most similar cases to a given anchor case based on a weighted sum of matching structural and property features in [find_similar_cases](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/similarity.py#L361-L405).
- **Case Comparison**: Direct side-by-side comparison of two cases, computing an explainable similarity score and documenting matching contributions in [compute_case_similarity](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/similarity.py#L309-L359).
- **Batch Similarity**: Computes a pairwise similarity matrix for a set of cases, returning all positively matching pairs sorted by score descending in [batch_similarity_matrix](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/similarity.py#L407-L442).
- **Repeat Offender Detection**: Identifies individuals accused in multiple distinct cases, returning histories sorted by case count descending in [detect_repeat_accused](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L162-L201).
- **Resolved Repeat Offenders**: Uses Entity Resolution to group spelling variations and alias profiles of same individuals, flagging repeat offenders across resolved entities in [detect_repeat_accused_resolved](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L590-L697).
- **Entity Resolution**: A deterministic, rule-based matching engine that normalizes strings, maps Indian phonetic variations, matches aliases, applies bigram Jaccard similarity, and boosts confidence based on address match in [resolve_person](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/entity_resolution.py#L117-L287).

---

## Network Analysis

- **Neighbor Search**: Safely retrieves immediate (1-hop) neighbors of a node by direction (in, out, or both) and optional edge type filters in [neighbors](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/utils.py#L194-L236) / [get_neighbors](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L325-L344).
- **Subgraph Extraction**: BFS extraction of a node-induced subgraph up to a depth cap, collecting all matching nodes and connecting edges for visualization in [get_subgraph](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L346-L403).
- **Related Cases**: Traverses bidirectional `LINKED_TO` edges to identify connected case clusters in [get_related_cases](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L134-L166).
- **Co-Accused Detection**: Extracts other accused persons associated with the same Case node via `ACCUSED_IN` incoming links in [get_co_accused](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L168-L201).
- **Officer Case Traversal**: Follows `INVESTIGATED_BY` edges in reverse to find all cases assigned to a specific investigating officer in [get_officer_cases](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L232-L260).
- **Dependency Chain**: Extracts outstanding investigation dependencies (blockers) linked to a Case node in [get_dependency_chain](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L262-L288).
- **Clock Traversal**: Retrieves all statutory clock instances associated with a Case node, sorted by remaining duration in [get_clock_instances](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L290-L320).
- **Evidence Traversal**: Traverses Case-to-Evidence edges (`CASE_HAS_EVIDENCE`) to retrieve linked physical or forensic evidence items in [get_evidence_for_case](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L428-L454).
- **Section Traversal**: Resolves specific statutory section charges (`CHARGED_UNDER`) associated with a Case in [get_sections_for_case](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py#L456-L481).

---

## Hotspot Analysis

- **Temporal Hotspots**: Flags dates with statistically abnormal case registration frequency based on daily counts in [detect_temporal_hotspots](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L514-L564).
- **District Hotspots**: Identifies geographic districts where registered cases exceed specified thresholds in [detect_district_hotspots](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L472-L509).
- **Dependency Hotspots**: Pinpoints cases with high quantities of pending investigation blockers in [detect_dependency_hotspots](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L409-L467).
- **Officer Workload**: Flags investigating officers whose assigned caseload exceeds thresholds, facilitating resource reallocation in [detect_high_workload_officers](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L362-L404).
- **Shared Phone Clusters**: Detects groups of individuals sharing the same phone cluster attribute across multiple cases in [detect_repeat_phone](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L207-L232).
- **Shared Vehicle Clusters**: Identifies groups of accused/complainants linked via shared vehicle registration IDs in [detect_repeat_vehicle](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L237-L262).
- **Shared Address Clusters**: Identifies groups of individuals linked to identical home/business addresses in [detect_repeat_address](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py#L267-L292).

---

## Statistics & Aggregation

- **Crime Summary**: Comprehensive multi-dimensional rollup summarizing total cases, stage distributions, risk bands, and offence categories in [case_counts](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py#L154-L178).
- **Crime by District**: Counts cases grouped by geographic district in [crime_count_by_district](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py#L66-L84).
- **Crime by Police Station**: Counts cases registered per local police station in [crime_count_by_station](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py#L86-L104).
- **Crime by Offence Category**: Groups case frequency based on type of offense category in [crime_count_by_offence_category](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py#L134-L151).
- **Graph Statistics**: Derives high-level topology metrics: density, node/edge distributions, average node degree, and isolated nodes count in [compute_graph_statistics](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/statistics.py#L89-L156).
- **Connected Components**: Computes weakly-connected components of the graph to identify isolated network units using a path-compressed Union-Find algorithm in [_UnionFind](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/statistics.py#L54-L84) and [connected_components](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/clustering.py#L100-L121).

---

## Testing

Summary of implemented unit and integration test coverage verifying the entire graph architecture:
- **Repository**: Evaluated in [test_graph_repository.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_graph_repository.py), covering query routing, single node loading, and role filter matches.
- **Loader**: Evaluated in [test_graph_loader.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_graph_loader.py), validating index construction, adjacency listings, and comprehensive constraint checks (orphans, missing nodes, duplicate IDs).
- **Services**: Evaluated in service-specific files ([test_graph_service.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_graph_service.py), [test_similarity_service.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_similarity_service.py), [test_network_service.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_network_service.py), [test_hotspot_service.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_hotspot_service.py), [test_offender_service.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_offender_service.py), [test_serializers.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_serializers.py)), verifying that all service methods return serialized, dictionary-mapped JSON data structures.
- **Algorithms**: Evaluated in algorithm test suites ([test_similarity.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_similarity.py), [test_traversals.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_traversals.py), [test_pattern_detection.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_pattern_detection.py), [test_aggregation.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_aggregation.py), [test_entity_resolution.py](file:///c:/Users/dyara/CaseClock/tests/graph/test_entity_resolution.py), [test_graph_foundation.py](file:///c:/Users/dyara/CaseClock/tests/test_graph_foundation.py)). Current test totals and verification status are reported in [`docs/benchmark-report.md`](benchmark-report.md), rather than duplicated here.
