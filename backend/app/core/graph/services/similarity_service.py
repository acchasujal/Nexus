"""
graph/services/similarity_service.py

Case similarity service: thin orchestration layer over the similarity algorithms.
All return values are JSON-serializable dicts.

Design rules
------------
* No similarity logic lives here -- all scoring is delegated to the algorithm
  module (backend.app.core.graph.algorithms.similarity).
* GraphService already exposes get_similar_cases and compare_two_cases
  for its own callers; this service provides the SimilarityService-specific
  response shapes required by dedicated similarity endpoints and dashboards.
* batch_similarity_matrix is not surfaced by any other service and is
  implemented here for the first time at the service layer.
"""

from __future__ import annotations

from typing import Any, Sequence

from backend.app.core.graph.algorithms.similarity import (
    batch_similarity_matrix,
    compute_case_similarity,
    find_similar_cases,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.serializers import serialize_dataclass


class SimilarityService:
    """
    Focused service for case-similarity intelligence.

    Initialized with a GraphRepository (which holds the GraphStore).
    Every public method returns JSON-serializable data.

    Notes
    -----
    This service deliberately limits its interface to operations backed by
    existing algorithms.  Do not add scoring logic, ML, or embeddings here.
    """

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    # =========================================================================
    # SIMILAR CASE LOOKUP
    # =========================================================================

    def get_similar_cases(
        self,
        case_id: str,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """
        Return the top-*k* most similar cases to *case_id*.

        Delegates entirely to ``find_similar_cases``.  Returns a "Case not
        found" error dict -- not an exception -- when the case does not exist
        in the graph.

        Used by: Case Detail -> Similar Cases tab

        Parameters
        ----------
        case_id : str
            The anchor case whose neighbours are to be found.
        top_k : int
            Maximum number of similar cases to return (default 10).

        Returns
        -------
        dict with keys:
            case_id            -- echo of the requested case id
            similar_case_count -- number of results returned
            similar_cases      -- list of serialized SimilarityResult dicts
        """
        store = self._repo.store
        results = find_similar_cases(store, case_id, top_k=top_k)

        if not results and store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}

        return {
            "case_id": case_id,
            "similar_case_count": len(results),
            "similar_cases": [serialize_dataclass(r) for r in results],
        }

    # =========================================================================
    # PAIRWISE COMPARISON
    # =========================================================================

    def compare_cases(
        self,
        case_a: str,
        case_b: str,
    ) -> dict[str, Any]:
        """
        Compute the explainable similarity score between two cases.

        Delegates entirely to ``compute_case_similarity``.  Returns a
        "Case not found" error dict -- not an exception -- when either case
        is absent from the graph.

        Used by: Side-by-side case comparison

        Parameters
        ----------
        case_a : str
            First case id.
        case_b : str
            Second case id.

        Returns
        -------
        dict with keys:
            case_a           -- echo of the first case id
            case_b           -- echo of the second case id
            similarity_score -- float in [0.0, 1.0]
            shared_features  -- list of matched feature names
        """
        store = self._repo.store

        # Validate existence before calling the algorithm so the error message
        # is explicit about which case is missing.
        if store.nodes.get(case_a) is None:
            return {"error": "Case not found", "case_id": case_a}
        if store.nodes.get(case_b) is None:
            return {"error": "Case not found", "case_id": case_b}

        result = compute_case_similarity(store, case_a, case_b)

        return {
            "case_a": result.case_a_id,
            "case_b": result.case_b_id,
            "similarity_score": result.score,
            "shared_features": result.matched_features,
        }

    # =========================================================================
    # BATCH MATRIX
    # =========================================================================

    def batch_similarity_matrix(
        self,
        case_ids: Sequence[str],
    ) -> dict[str, Any]:
        """
        Compute pairwise similarity for a list of case ids.

        Each unique pair (A, B) where A is less than B is scored once by the algorithm.
        Only pairs with score > 0 are included in the result.

        Delegates entirely to the module-level ``batch_similarity_matrix``
        algorithm function.

        Used by: Bulk analysis / investigative clustering views

        Parameters
        ----------
        case_ids : sequence of str
            Case ids to include in the pairwise comparison.

        Returns
        -------
        dict with keys:
            case_ids   -- the input case id list (echoed)
            pair_count -- number of scored pairs returned
            pairs      -- list of serialized SimilarityResult dicts,
                          sorted by score descending
        """
        store = self._repo.store
        results = batch_similarity_matrix(store, case_ids)

        return {
            "case_ids": list(case_ids),
            "pair_count": len(results),
            "pairs": [serialize_dataclass(r) for r in results],
        }
