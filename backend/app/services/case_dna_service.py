"""backend/app/services/case_dna_service.py

Case DNA Multi-Dimensional Structural Similarity Service (P2).
Computes explainable, 5-vector topological similarity between criminal cases
and provides immutable audit logging for investigations.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.graph.algorithms.case_dna import match_case_dna
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import CaseDNAMatchResponse

logger = logging.getLogger(__name__)


class CaseDNAService:
    """Application-layer service managing Case DNA structural matching."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        audit_service: AuditService,
    ) -> None:
        self.repo = repository
        self.audit = audit_service

    def get_case_dna_matches(
        self,
        case_id: str,
        top_k: int = 10,
        principal: Principal | None = None,
    ) -> CaseDNAMatchResponse:
        """Find structurally similar cases using 5-vector topological Case DNA profiles."""
        store = getattr(self.repo, "store", None)
        if store is None and hasattr(self.repo, "to_graph_store"):
            store = self.repo.to_graph_store()
        if store is None:
            return CaseDNAMatchResponse(

                target_case_id=case_id,
                similar_cases=[],
                average_similarity=0.0,
                highest_similarity=0.0,
                top_shared_entities=[],
            )

        response = match_case_dna(store, target_case_id=case_id, top_k=top_k)

        # Append immutable audit event
        try:
            actor_id = principal.user_id if principal else "SYSTEM"
            self.audit.record(
                event_type=AuditEventType.SIMILARITY_SEARCH_EXECUTED,
                actor_id=actor_id,
                case_id=case_id,
                entity_id=case_id,
                entity_type="Case",
                details={
                    "top_k": top_k,
                    "matches_found": len(response.similar_cases),
                    "highest_similarity": response.highest_similarity,
                    "average_similarity": response.average_similarity,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record audit log for Case DNA match on {case_id}: {e}")

        return response

