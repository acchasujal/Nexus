"""backend/app/core/graph/algorithms — deterministic graph algorithm modules."""

from backend.app.core.graph.algorithms.bridges import (
    BridgeCandidateResult,
    compute_person_bridge_intelligence,
    get_network_centrality_summary,
    top_bridge_entities,
)
from backend.app.core.graph.algorithms.centrality import (
    PersonBetweennessResult,
    PersonDegreeResult,
    compute_person_betweenness_centrality,
    compute_person_degree_centrality,
)
from backend.app.core.graph.algorithms.communities import (
    NetworkCommunitiesSummary,
    PersonCommunityResult,
    detect_louvain_communities,
    generate_stable_community_id,
)
from backend.app.core.graph.algorithms.cross_case import (
    detect_cross_case_bridges,
)
from backend.app.core.graph.algorithms.entity_resolution import (
    ResolutionMatch,
    jaccard_similarity,
    normalize_text,
    phonetic_normalize,
    resolve_person,
)
from backend.app.core.graph.algorithms.pattern_rules import (
    PatternFinding,
    detect_all_suspicious_patterns,
    detect_circular_repeated_financial_flow,
    detect_communication_burst_near_event,
    detect_shared_phone_device,
)
from backend.app.core.graph.algorithms.projection import (
    project_person_graph,
    project_person_nodes_and_edges,
)
from backend.app.core.graph.algorithms.snapshot_diff import (
    DiffSummaryMetrics,
    GraphSnapshotDiff,
    NodeDiffRecord,
    NodeFieldChange,
    RelationshipDiffRecord,
    RelationshipFieldChange,
    diff_graph_snapshots,
)

__all__ = [
    "ResolutionMatch",
    "resolve_person",
    "phonetic_normalize",
    "normalize_text",
    "jaccard_similarity",
    "project_person_graph",
    "project_person_nodes_and_edges",
    "PersonDegreeResult",
    "PersonBetweennessResult",
    "compute_person_degree_centrality",
    "compute_person_betweenness_centrality",
    "BridgeCandidateResult",
    "compute_person_bridge_intelligence",
    "top_bridge_entities",
    "get_network_centrality_summary",
    "PersonCommunityResult",
    "NetworkCommunitiesSummary",
    "generate_stable_community_id",
    "detect_louvain_communities",
    "PatternFinding",
    "detect_shared_phone_device",
    "detect_communication_burst_near_event",
    "detect_circular_repeated_financial_flow",
    "detect_all_suspicious_patterns",
    "detect_cross_case_bridges",
    "DiffSummaryMetrics",
    "GraphSnapshotDiff",
    "NodeDiffRecord",
    "NodeFieldChange",
    "RelationshipDiffRecord",
    "RelationshipFieldChange",
    "diff_graph_snapshots",
]




