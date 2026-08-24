"""backend/app/core/graph/algorithms — deterministic graph algorithm modules."""

from backend.app.core.graph.algorithms.entity_resolution import (
    ResolutionMatch,
    resolve_person,
    phonetic_normalize,
    normalize_text,
    jaccard_similarity,
)
from backend.app.core.graph.algorithms.projection import (
    project_person_graph,
    project_person_nodes_and_edges,
)
from backend.app.core.graph.algorithms.centrality import (
    PersonDegreeResult,
    PersonBetweennessResult,
    compute_person_degree_centrality,
    compute_person_betweenness_centrality,
)
from backend.app.core.graph.algorithms.bridges import (
    BridgeCandidateResult,
    compute_person_bridge_intelligence,
    top_bridge_entities,
    get_network_centrality_summary,
)
from backend.app.core.graph.algorithms.communities import (
    PersonCommunityResult,
    NetworkCommunitiesSummary,
    generate_stable_community_id,
    detect_louvain_communities,
)
from backend.app.core.graph.algorithms.pattern_rules import (
    PatternFinding,
    detect_shared_phone_device,
    detect_communication_burst_near_event,
    detect_circular_repeated_financial_flow,
    detect_all_suspicious_patterns,
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
]




