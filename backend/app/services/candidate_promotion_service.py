"""backend/app/services/candidate_promotion_service.py

Investigator Confirmation & Candidate Promotion Service (Phase P1-C).

Lifecycle:
  P1B CANDIDATE
        ↓
  INVESTIGATOR REVIEW
        ↓
  ACCEPT / REJECT
        ↓
  VALIDATION
        ↓
  AUTHORITATIVE GRAPH MUTATION
        ↓
  PROVENANCE & AUDIT
        ↓
  REVIEWABLE HISTORY

Non-Negotiable Invariants:
  1. No candidate enters authoritative graph without an explicit authorized decision.
  2. Zero LLM calls in promotion path (100% deterministic code).
  3. Server-side RBAC verification via EvidenceAuthorizationPolicy.
  4. Double-click idempotency and stale candidate protection.
  5. Relationship promotion strictly requires both source and target to be authoritative in graph.
  6. Rejection never mutates the graph.
  7. On mutation failure: clean rollback, no false-success audit, candidate remains reviewable.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.auth.principal import Principal
from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.graph_mutation_service import GraphMutationService
from shared.contracts.api import (
    AcceptExistingEntityRequest,
    AcceptNewEntityRequest,
    AcceptRelationshipRequest,
    CandidateDecisionAction,
    CandidateDecisionResponse,
    CandidateDecisionStatus,
    RejectCandidateRequest,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CandidatePromotionService:
    """Manages investigator reviews, confirmations, rejections, and graph mutations."""

    def __init__(
        self,
        repository: Any,
        mutation_service: GraphMutationService,
        audit_service: AuditService,
        auth_policy: EvidenceAuthorizationPolicy,
    ) -> None:
        self.repo = repository
        self.mutator = mutation_service
        self.audit = audit_service
        self.auth = auth_policy

    # ── Accept Candidate -> Link to Existing Authoritative Entity ────────────

    def accept_existing_entity(
        self,
        candidate_id: str,
        request: AcceptExistingEntityRequest,
        principal: Principal,
    ) -> CandidateDecisionResponse:
        """Link a candidate entity to an existing canonical graph node."""
        candidate = self.repo.get_candidate_entity(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate entity '{candidate_id}' not found",
            )

        case_id = request.case_id or candidate.get("case_id")

        # 1. RBAC Check
        authorized, reason = self.auth.can_decide_candidate(principal, case_id)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {reason}",
            )

        # 2. Idempotency Check
        prior_decisions = self.repo.get_candidate_decisions(candidate_id)
        for dec in prior_decisions:
            if dec.get("status") == CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value:
                if dec.get("target_id") == request.target_canonical_id:
                    # Idempotent re-submission: return existing decision without re-mutating
                    return CandidateDecisionResponse(**dec)
            if dec.get("status") in (
                CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value,
                CandidateDecisionStatus.REJECTED.value,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate '{candidate_id}' has already been decided as {dec.get('status')}",
                )

        target_id = request.target_canonical_id
        nodes = getattr(self.repo, "nodes", {})
        if target_id not in nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target canonical entity '{target_id}' does not exist in graph",
            )

        officer = principal.get_officer_identity()
        doc_id = candidate.get("source_document_id", "UNKNOWN")
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"

        # 3. Graph Mutation with failure handling
        try:
            self.mutator.link_candidate_to_entity(
                canonical_id=target_id,
                candidate_entity=candidate,
                document_id=doc_id,
                case_id=case_id,
                officer_id=officer.officer_id,
            )
        except Exception as exc:
            logger.error("Failed to link candidate %s to entity %s: %s", candidate_id, target_id, exc)
            self.audit.record(
                event_type=AuditEventType.CANDIDATE_PROMOTION_FAILED,
                actor_id=officer.officer_id,
                case_id=case_id,
                entity_type="CandidateEntity",
                entity_id=candidate_id,
                details={"error": str(exc), "target_canonical_id": target_id, "action": "ACCEPT_EXISTING"},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph mutation failed: {exc}",
            ) from exc

        # 4. Update Candidate Status & Persist Decision
        self.repo.update_candidate_entity_status(
            candidate_id=candidate_id,
            status=CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value,
            resulting_graph_id=target_id,
        )

        decision_data = {
            "decision_id": decision_id,
            "candidate_id": candidate_id,
            "candidate_type": "ENTITY",
            "action": CandidateDecisionAction.ACCEPT_EXISTING.value,
            "status": CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value,
            "decided_by": officer.officer_id,
            "decided_at": _utcnow().isoformat(),
            "target_id": target_id,
            "resulting_graph_id": target_id,
            "reason": None,
            "notes": request.notes,
        }

        # 5. Audit Logging
        audit_event_id = self.audit.record(
            event_type=AuditEventType.ENTITY_LINKED,
            actor_id=officer.officer_id,
            case_id=case_id,
            entity_type="CandidateEntity",
            entity_id=candidate_id,
            details={
                "canonical_entity_id": target_id,
                "document_id": doc_id,
                "case_id": case_id,
                "notes": request.notes,
            },
        )
        decision_data["audit_event_id"] = audit_event_id

        self.repo.store_candidate_decision(decision_data)
        return CandidateDecisionResponse(**decision_data)

    # ── Accept Candidate -> Create New Authoritative Entity ──────────────────

    def accept_new_entity(
        self,
        candidate_id: str,
        request: AcceptNewEntityRequest,
        principal: Principal,
    ) -> CandidateDecisionResponse:
        """Promote a candidate entity into a brand new canonical graph node."""
        candidate = self.repo.get_candidate_entity(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate entity '{candidate_id}' not found",
            )

        case_id = request.case_id or candidate.get("case_id")

        # 1. RBAC Check
        authorized, reason = self.auth.can_decide_candidate(principal, case_id)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {reason}",
            )

        # 2. Idempotency Check
        prior_decisions = self.repo.get_candidate_decisions(candidate_id)
        for dec in prior_decisions:
            if dec.get("status") == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value:
                return CandidateDecisionResponse(**dec)
            if dec.get("status") in (
                CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value,
                CandidateDecisionStatus.REJECTED.value,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate '{candidate_id}' has already been decided as {dec.get('status')}",
                )

        officer = principal.get_officer_identity()
        doc_id = candidate.get("source_document_id", "UNKNOWN")
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"

        # Merge candidate properties with request properties
        combined_props = dict(candidate.get("properties") or {})
        if request.properties:
            combined_props.update(request.properties)

        created_node_id: str | None = None

        # 3. Graph Mutation with failure rollback
        try:
            created_node = self.mutator.create_canonical_entity(
                entity_type=request.entity_type or candidate.get("entity_type", "Person"),
                canonical_name=request.canonical_name or candidate.get("surface_text", ""),
                properties=combined_props,
                document_id=doc_id,
                case_id=case_id,
                officer_id=officer.officer_id,
            )
            created_node_id = created_node["id"]
        except Exception as exc:
            logger.error("Failed to create canonical entity for candidate %s: %s", candidate_id, exc)
            if created_node_id:
                self.mutator.rollback_entity_creation(created_node_id)
            self.audit.record(
                event_type=AuditEventType.CANDIDATE_PROMOTION_FAILED,
                actor_id=officer.officer_id,
                case_id=case_id,
                entity_type="CandidateEntity",
                entity_id=candidate_id,
                details={"error": str(exc), "action": "ACCEPT_NEW"},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph mutation failed: {exc}",
            ) from exc

        # 4. Update Candidate Status & Persist Decision
        self.repo.update_candidate_entity_status(
            candidate_id=candidate_id,
            status=CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value,
            resulting_graph_id=created_node_id,
        )

        decision_data = {
            "decision_id": decision_id,
            "candidate_id": candidate_id,
            "candidate_type": "ENTITY",
            "action": CandidateDecisionAction.ACCEPT_NEW.value,
            "status": CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value,
            "decided_by": officer.officer_id,
            "decided_at": _utcnow().isoformat(),
            "target_id": created_node_id,
            "resulting_graph_id": created_node_id,
            "reason": None,
            "notes": request.notes,
        }

        # 5. Audit Logging
        audit_event_id = self.audit.record(
            event_type=AuditEventType.ENTITY_PROMOTED,
            actor_id=officer.officer_id,
            case_id=case_id,
            entity_type="CandidateEntity",
            entity_id=candidate_id,
            details={
                "created_canonical_id": created_node_id,
                "canonical_name": request.canonical_name,
                "entity_type": request.entity_type,
                "document_id": doc_id,
                "case_id": case_id,
                "notes": request.notes,
            },
        )
        decision_data["audit_event_id"] = audit_event_id

        self.repo.store_candidate_decision(decision_data)
        return CandidateDecisionResponse(**decision_data)

    # ── Accept Candidate Relationship -> Authoritative Graph Edge ───────────

    def accept_relationship(
        self,
        relationship_id: str,
        request: AcceptRelationshipRequest,
        principal: Principal,
    ) -> CandidateDecisionResponse:
        """Promote a candidate relationship into an authoritative graph edge."""
        cand_rel = self.repo.get_candidate_relationship(relationship_id)
        if not cand_rel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate relationship '{relationship_id}' not found",
            )

        case_id = request.case_id or cand_rel.get("case_id")

        # 1. RBAC Check
        authorized, reason = self.auth.can_decide_candidate(principal, case_id)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {reason}",
            )

        # 2. Idempotency Check
        prior_decisions = self.repo.get_candidate_decisions(relationship_id)
        for dec in prior_decisions:
            if dec.get("status") == CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value:
                return CandidateDecisionResponse(**dec)
            if dec.get("status") == CandidateDecisionStatus.REJECTED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate relationship '{relationship_id}' has already been rejected",
                )

        # 3. Prerequisites: BOTH endpoints MUST exist in authoritative graph
        src_id = request.source_canonical_id
        tgt_id = request.target_canonical_id
        nodes = getattr(self.repo, "nodes", {})

        if src_id not in nodes or tgt_id not in nodes:
            missing = []
            if src_id not in nodes:
                missing.append(f"source '{src_id}'")
            if tgt_id not in nodes:
                missing.append(f"target '{tgt_id}'")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot promote relationship: {', '.join(missing)} does not exist in authoritative graph. "
                    "Both entities must be resolved or promoted to the authoritative graph first."
                ),
            )

        officer = principal.get_officer_identity()
        doc_id = cand_rel.get("source_document_id", "UNKNOWN")
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        edge_type = request.relationship_type or cand_rel.get("relationship_type", "CONNECTED_TO")

        created_edge_id: str | None = None

        # 4. Graph Mutation with failure rollback
        try:
            edge = self.mutator.create_authoritative_relationship(
                source_id=src_id,
                target_id=tgt_id,
                edge_type=edge_type,
                properties=request.properties or {},
                document_id=doc_id,
                case_id=case_id,
                officer_id=officer.officer_id,
            )
            created_edge_id = str(edge.get("id"))
        except Exception as exc:
            logger.error("Failed to create relationship for candidate rel %s: %s", relationship_id, exc)
            if created_edge_id:
                self.mutator.rollback_edge_creation(created_edge_id)
            self.audit.record(
                event_type=AuditEventType.CANDIDATE_PROMOTION_FAILED,
                actor_id=officer.officer_id,
                case_id=case_id,
                entity_type="CandidateRelationship",
                entity_id=relationship_id,
                details={"error": str(exc), "action": "ACCEPT_RELATIONSHIP"},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph relationship mutation failed: {exc}",
            ) from exc

        # 5. Update Candidate Status & Persist Decision
        self.repo.update_candidate_relationship_status(
            relationship_id=relationship_id,
            status=CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value,
            resulting_edge_id=created_edge_id,
        )

        decision_data = {
            "decision_id": decision_id,
            "candidate_id": relationship_id,
            "candidate_type": "RELATIONSHIP",
            "action": CandidateDecisionAction.ACCEPT_RELATIONSHIP.value,
            "status": CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value,
            "decided_by": officer.officer_id,
            "decided_at": _utcnow().isoformat(),
            "target_id": created_edge_id,
            "resulting_graph_id": created_edge_id,
            "reason": None,
            "notes": request.notes,
        }

        # 6. Audit Logging
        audit_event_id = self.audit.record(
            event_type=AuditEventType.RELATIONSHIP_PROMOTED,
            actor_id=officer.officer_id,
            case_id=case_id,
            entity_type="CandidateRelationship",
            entity_id=relationship_id,
            details={
                "source_id": src_id,
                "target_id": tgt_id,
                "edge_type": edge_type,
                "edge_id": created_edge_id,
                "document_id": doc_id,
                "case_id": case_id,
                "notes": request.notes,
            },
        )
        decision_data["audit_event_id"] = audit_event_id

        self.repo.store_candidate_decision(decision_data)
        return CandidateDecisionResponse(**decision_data)

    # ── Reject Candidate (Entity or Relationship) ────────────────────────────

    def reject_candidate(
        self,
        candidate_id: str,
        request: RejectCandidateRequest,
        principal: Principal,
        candidate_type: str = "ENTITY",
    ) -> CandidateDecisionResponse:
        """Reject a candidate entity or relationship.

        Strict Safeguard: Zero graph mutation occurs. Candidate is preserved in repository
        with status REJECTED for auditability.
        """
        if candidate_type == "ENTITY":
            item = self.repo.get_candidate_entity(candidate_id)
        else:
            item = self.repo.get_candidate_relationship(candidate_id)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_type.lower()} '{candidate_id}' not found",
            )

        case_id = item.get("case_id")

        # 1. RBAC Check
        authorized, reason = self.auth.can_decide_candidate(principal, case_id)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {reason}",
            )

        # 2. Idempotency Check
        prior_decisions = self.repo.get_candidate_decisions(candidate_id)
        for dec in prior_decisions:
            if dec.get("status") == CandidateDecisionStatus.REJECTED.value:
                return CandidateDecisionResponse(**dec)

        officer = principal.get_officer_identity()
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"

        # 3. Update Status (No graph mutation!)
        if candidate_type == "ENTITY":
            self.repo.update_candidate_entity_status(
                candidate_id=candidate_id,
                status=CandidateDecisionStatus.REJECTED.value,
            )
        else:
            self.repo.update_candidate_relationship_status(
                relationship_id=candidate_id,
                status=CandidateDecisionStatus.REJECTED.value,
            )

        decision_data = {
            "decision_id": decision_id,
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "action": CandidateDecisionAction.REJECT.value,
            "status": CandidateDecisionStatus.REJECTED.value,
            "decided_by": officer.officer_id,
            "decided_at": _utcnow().isoformat(),
            "target_id": None,
            "resulting_graph_id": None,
            "reason": request.reason,
            "notes": request.notes,
        }

        # 4. Audit Logging
        audit_event_id = self.audit.record(
            event_type=AuditEventType.CANDIDATE_REJECTED,
            actor_id=officer.officer_id,
            case_id=case_id,
            entity_type=f"Candidate{candidate_type.capitalize()}",
            entity_id=candidate_id,
            details={
                "reason": request.reason,
                "notes": request.notes,
                "case_id": case_id,
                "document_id": item.get("source_document_id"),
            },
        )
        decision_data["audit_event_id"] = audit_event_id

        self.repo.store_candidate_decision(decision_data)
        return CandidateDecisionResponse(**decision_data)

    # ── Retrieve Candidate Decisions ─────────────────────────────────────────

    def get_candidate_decisions(
        self,
        candidate_id: str,
        principal: Principal,
    ) -> list[CandidateDecisionResponse]:
        """Retrieve all recorded decisions for a given candidate."""
        if principal.is_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view candidate decision history",
            )
        decisions = self.repo.get_candidate_decisions(candidate_id)
        return [CandidateDecisionResponse(**d) for d in decisions]
