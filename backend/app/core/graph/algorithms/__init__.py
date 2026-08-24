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

__all__ = [
    "ResolutionMatch",
    "resolve_person",
    "phonetic_normalize",
    "normalize_text",
    "jaccard_similarity",
    "project_person_graph",
    "project_person_nodes_and_edges",
]

