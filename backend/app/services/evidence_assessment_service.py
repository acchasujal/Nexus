"""backend/app/services/evidence_assessment_service.py

First-Class Evidence Assessment Service for the NEXUS Criminal Intelligence Platform (A5).

Provides:
  - EvidenceAssessmentService: domain service managing explainable evidence assessments
    grounding claims, relationships, entities, and events in authoritative evidence.

Governing Principles:
  - Epistemic clarity: strictly SUPPORTS, CONFLICTS, MISSING, INFERRED, VERIFIED.
  - Zero predictive guilt / confidence scoring: no numerical scores, probabilities, or guilt bias.
  - Deterministic before generative: deterministic verification and provenance preservation.
  - Audit and IntelligenceEvent integration: emits EVIDENCE_ASSESSMENT_CREATED / REVISED
    and A3 EVIDENCE_ASSESSED events.
  - Decoupled lifecycle: does NOT mutate graph nodes/edges, does NOT trigger A8 closed-loop
    propagation, and does NOT auto-complete A7 verification tasks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.ingestion.identifiers import make_evidence_assessment_id
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from shared.contracts.api import (
    AssessmentBasis,
    AssessmentRevisionHistoryItem,
    CreateEvidenceAssessmentRequest,
    CreateIntelligenceEventRequest,
    EpistemicState,
    EvidenceAssessment,
    EvidenceAssessmentItem,
    EvidenceAssessmentListResponse,
    IntelligenceEventType,
    ReviseEvidenceAssessmentRequest,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val:
        try:
            cleaned = val.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utcnow()


class EvidenceAssessmentService:
    """
    Application-layer service managing first-class investigator evidence assessments.
    Validates claims, authoritative evidence references, case clearances, provenance,
    append-only revision history, and audit/intelligence event notifications.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        evidence_service: Any | None = None,
        intelligence_event_service: IntelligenceEventService | None = None,
        auth_policy: EvidenceAuthorizationPolicy | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._evidence_svc = evidence_service
        self._intel_svc = intelligence_event_service
        self._auth = auth_policy

    # ── Evidence Reference Validation & Provenance Extraction ────────────────

    def _resolve_and_validate_evidence(
        self,
        evidence_id: str,
        case_id: str,
        actor_id: str = "system",
    ) -> dict[str, Any]:
        """
        Validate that an evidence record exists and is accessible for the case.
        Returns a dictionary of provenance attributes.
        Raises ValueError if nonexistent or invalid.
        """
        clean_ev_id = str(evidence_id).strip()
        if not clean_ev_id:
            raise ValueError("Evidence reference ID must not be empty.")

        # 1. Try EvidenceService if available
        if self._evidence_svc and hasattr(self._evidence_svc, "get_evidence_by_id"):
            ev_item = self._evidence_svc.get_evidence_by_id(clean_ev_id, actor_id=actor_id, suppress_audit=True)
            if ev_item:
                ev_case = getattr(ev_item, "case_id", None)
                if ev_case and str(ev_case).strip() and str(ev_case).strip() != case_id:
                    logger.warning(
                        "Evidence %s is associated with case %s, being referenced in assessment for case %s",
                        clean_ev_id,
                        ev_case,
                        case_id,
                    )
                prov = getattr(ev_item, "provenance", None)
                return {
                    "source_id": getattr(prov, "source_id", clean_ev_id) if prov else clean_ev_id,
                    "source_type": getattr(prov, "source_type", "RECORD") if prov else "RECORD",
                    "observed_at": getattr(prov, "timestamp", None) if prov else getattr(ev_item, "collected_at", None),
                    "extracted_fact": getattr(prov, "extracted_fact", "") if prov else getattr(ev_item, "description", ""),
                }

        # 2. Check repository source_records directly
        source_records = getattr(self._repo, "source_records", {})
        if clean_ev_id in source_records:
            srec = source_records[clean_ev_id]
            ts_raw = srec.get("occurred_at")
            return {
                "source_id": clean_ev_id,
                "source_type": srec.get("source_type", "RECORD"),
                "observed_at": _parse_datetime(ts_raw) if ts_raw else _utcnow(),
                "extracted_fact": srec.get("raw_excerpt", ""),
            }

        # 3. Check graph store edges for matching provenance
        if hasattr(self._repo, "to_graph_store"):
            store = self._repo.to_graph_store()
            for _etype, edges in store.edge_index.items():
                for edge in edges:
                    props = getattr(edge, "properties", {}) or {}
                    prov = props.get("provenance") or {}
                    if isinstance(prov, dict) and prov.get("source_id") == clean_ev_id:
                        return {
                            "source_id": clean_ev_id,
                            "source_type": prov.get("source_type", "RECORD"),
                            "observed_at": _parse_datetime(prov.get("timestamp")),
                            "extracted_fact": prov.get("extracted_fact", ""),
                        }

        raise ValueError(f"Referenced evidence '{clean_ev_id}' does not exist in authoritative records.")

    # ── Assessment Creation ───────────────────────────────────────────────────

    def create_assessment(
        self,
        request: CreateEvidenceAssessmentRequest,
        principal: Principal | None = None,
    ) -> EvidenceAssessment:
        """
        Validate, deterministically identify, and persist an EvidenceAssessment.
        Idempotent: Re-creating an existing assessment returns the stored record.
        """
        if not request.case_id or not request.case_id.strip():
            raise ValueError("EvidenceAssessment requires a valid, non-empty case_id.")
        if not request.claim or not request.claim.strip():
            raise ValueError("EvidenceAssessment requires a valid, non-empty claim.")
        if not request.rationale or not request.rationale.strip():
            raise ValueError("EvidenceAssessment requires a valid, non-empty rationale.")
        if len(request.rationale.strip()) < 5:
            raise ValueError("EvidenceAssessment rationale must provide an explainable evidence basis.")

        clean_case_id = request.case_id.strip()
        clean_claim = request.claim.strip()
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "system"

        # Enforce Case RBAC Clearance
        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, clean_case_id)
            if not allowed:
                raise PermissionError(
                    f"Access denied: cannot create evidence assessment for case '{clean_case_id}': {reason}"
                )

        # Validate all referenced evidence IDs and gather provenance
        all_referenced_ids = list(
            dict.fromkeys(
                [eid.strip() for eid in request.evidence_ids if eid.strip()]
                + [eid.strip() for eid in request.supporting_evidence_ids if eid.strip()]
                + [eid.strip() for eid in request.conflicting_evidence_ids if eid.strip()]
            )
        )

        resolved_source_ids: set[str] = set()
        resolved_source_types: set[str] = set()
        observed_timestamps: list[datetime] = []
        provenance_refs: list[str] = []

        for ev_id in all_referenced_ids:
            prov_data = self._resolve_and_validate_evidence(
                evidence_id=ev_id,
                case_id=clean_case_id,
                actor_id=actor_id,
            )
            resolved_source_ids.add(prov_data["source_id"])
            resolved_source_types.add(prov_data["source_type"])
            if prov_data.get("observed_at"):
                observed_timestamps.append(prov_data["observed_at"])
            provenance_refs.append(f"{prov_data['source_type']}:{prov_data['source_id']}")

        # Determine observed_at as earliest or newest timestamp
        observed_at = min(observed_timestamps) if observed_timestamps else None

        # Deterministic canonical assessment ID: evasmt-{digest12}
        discriminator = str(request.target_edge_id or request.target_entity_id or "").strip()
        assessment_id = make_evidence_assessment_id(
            case_id=clean_case_id,
            claim=clean_claim,
            state=request.state.value,
            discriminator=discriminator,
        )

        # Idempotency check: if assessment exists, return stored entity
        existing = self._repo.get_evidence_assessment(assessment_id)
        if existing:
            return EvidenceAssessment(**existing)

        now = _utcnow()
        assessment = EvidenceAssessment(
            assessment_id=assessment_id,
            case_id=clean_case_id,
            created_at=now,
            updated_at=now,
            claim=clean_claim,
            claim_type=request.claim_type,
            target_entity_id=request.target_entity_id,
            target_edge_id=request.target_edge_id,
            target_event_id=request.target_event_id,
            intelligence_event_id=request.intelligence_event_id,
            verification_task_id=request.verification_task_id,
            state=request.state,
            rationale=request.rationale.strip(),
            assessment_basis=request.assessment_basis,
            evidence_ids=all_referenced_ids,
            supporting_evidence_ids=[eid.strip() for eid in request.supporting_evidence_ids if eid.strip()],
            conflicting_evidence_ids=[eid.strip() for eid in request.conflicting_evidence_ids if eid.strip()],
            missing_evidence_types=list(request.missing_evidence_types),
            source_ids=sorted(list(resolved_source_ids)),
            source_types=sorted(list(resolved_source_types)),
            observed_at=observed_at,
            ingested_at=now,
            provenance_refs=provenance_refs,
            history=[],
        )

        # Persist in repository
        self._repo.save_evidence_assessment(assessment.model_dump(mode="json"))

        # Audit Event
        self._audit.record(
            AuditEventType.EVIDENCE_ASSESSMENT_CREATED,
            actor_id=actor_id,
            case_id=clean_case_id,
            entity_id=assessment.assessment_id,
            entity_type="EvidenceAssessment",
            details={
                "claim": clean_claim,
                "claim_type": request.claim_type,
                "state": request.state.value,
                "basis": request.assessment_basis.value,
                "evidence_count": len(all_referenced_ids),
                "rationale": request.rationale.strip(),
            },
        )

        # Emit A3 IntelligenceEvent (EVIDENCE_ASSESSED)
        if self._intel_svc:
            try:
                self._intel_svc.record_event(
                    CreateIntelligenceEventRequest(
                        event_type=IntelligenceEventType.EVIDENCE_ASSESSED,
                        case_id=clean_case_id,
                        evidence_refs=all_referenced_ids,
                        related_entity_ids=[request.target_entity_id] if request.target_entity_id else [],
                        related_edge_ids=[request.target_edge_id] if request.target_edge_id else [],
                        source_type="EVIDENCE_ASSESSMENT",
                        actor_id=actor_id,
                        title=f"Evidence Assessed: {clean_claim[:60]}",
                        description=request.rationale.strip(),
                        payload={
                            "assessment_id": assessment.assessment_id,
                            "claim": clean_claim,
                            "state": request.state.value,
                            "basis": request.assessment_basis.value,
                            "target_event_id": request.target_event_id,
                            "verification_task_id": request.verification_task_id,
                        },
                    ),
                    principal=principal,
                )
            except Exception as exc:
                logger.warning("Failed to emit IntelligenceEvent for assessment %s: %s", assessment.assessment_id, exc)

        return assessment

    # ── Assessment Revision & History ─────────────────────────────────────────

    def revise_assessment(
        self,
        assessment_id: str,
        request: ReviseEvidenceAssessmentRequest,
        principal: Principal | None = None,
    ) -> EvidenceAssessment:
        """
        Append-only auditable revision of an existing EvidenceAssessment.
        Preserves complete revision history with actor, timestamp, prior state,
        and explanation without destructive overwriting.
        """
        raw = self._repo.get_evidence_assessment(str(assessment_id))
        if not raw:
            raise KeyError(f"EvidenceAssessment '{assessment_id}' does not exist.")

        existing = EvidenceAssessment(**raw)
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "system"

        # Enforce Case RBAC Clearance
        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, existing.case_id)
            if not allowed:
                raise PermissionError(
                    f"Access denied: cannot revise evidence assessment for case '{existing.case_id}': {reason}"
                )

        if not request.rationale or not request.rationale.strip():
            raise ValueError("Assessment revision requires an explainable rationale.")

        # Validate additional evidence references if provided
        new_evidence_ids = [eid.strip() for eid in request.additional_evidence_ids if eid.strip()]
        for ev_id in new_evidence_ids:
            self._resolve_and_validate_evidence(
                evidence_id=ev_id,
                case_id=existing.case_id,
                actor_id=actor_id,
            )

        updated_evidence_ids = list(dict.fromkeys(existing.evidence_ids + new_evidence_ids))
        updated_supporting = (
            [eid.strip() for eid in request.supporting_evidence_ids if eid.strip()]
            if request.supporting_evidence_ids is not None
            else existing.supporting_evidence_ids
        )
        updated_conflicting = (
            [eid.strip() for eid in request.conflicting_evidence_ids if eid.strip()]
            if request.conflicting_evidence_ids is not None
            else existing.conflicting_evidence_ids
        )
        updated_missing = (
            list(request.missing_evidence_types)
            if request.missing_evidence_types is not None
            else existing.missing_evidence_types
        )

        # Build immutable history item
        now = _utcnow()
        revision_item = AssessmentRevisionHistoryItem(
            revision_number=len(existing.history) + 1,
            from_state=existing.state,
            to_state=request.state,
            actor_id=actor_id,
            timestamp=now,
            rationale=request.rationale.strip(),
            evidence_ids=updated_evidence_ids,
        )

        history = list(existing.history)
        history.append(revision_item)

        revised = existing.model_copy(
            update={
                "state": request.state,
                "rationale": request.rationale.strip(),
                "assessment_basis": request.assessment_basis or existing.assessment_basis,
                "evidence_ids": updated_evidence_ids,
                "supporting_evidence_ids": updated_supporting,
                "conflicting_evidence_ids": updated_conflicting,
                "missing_evidence_types": updated_missing,
                "updated_at": now,
                "history": history,
            }
        )

        # Update in repository
        self._repo.update_evidence_assessment(revised.model_dump(mode="json"))

        # Audit Event
        self._audit.record(
            AuditEventType.EVIDENCE_ASSESSMENT_REVISED,
            actor_id=actor_id,
            case_id=existing.case_id,
            entity_id=revised.assessment_id,
            entity_type="EvidenceAssessment",
            details={
                "previous_state": existing.state.value,
                "new_state": request.state.value,
                "revision_number": revision_item.revision_number,
                "rationale": request.rationale.strip(),
            },
        )

        # Emit A3 IntelligenceEvent (EVIDENCE_ASSESSED)
        if self._intel_svc:
            try:
                self._intel_svc.record_event(
                    CreateIntelligenceEventRequest(
                        event_type=IntelligenceEventType.EVIDENCE_ASSESSED,
                        case_id=existing.case_id,
                        evidence_refs=updated_evidence_ids,
                        related_entity_ids=[existing.target_entity_id] if existing.target_entity_id else [],
                        related_edge_ids=[existing.target_edge_id] if existing.target_edge_id else [],
                        source_type="EVIDENCE_ASSESSMENT_REVISION",
                        actor_id=actor_id,
                        title=f"Evidence Assessment Revised: {existing.claim[:60]}",
                        description=request.rationale.strip(),
                        payload={
                            "assessment_id": revised.assessment_id,
                            "from_state": existing.state.value,
                            "to_state": request.state.value,
                            "revision_number": revision_item.revision_number,
                        },
                    ),
                    principal=principal,
                )
            except Exception as exc:
                logger.warning("Failed to emit IntelligenceEvent for revision %s: %s", revised.assessment_id, exc)

        return revised

    # ── Query & Retrieval Methods ─────────────────────────────────────────────

    def get_assessment(
        self,
        assessment_id: str,
        principal: Principal | None = None,
    ) -> EvidenceAssessment | None:
        """Retrieve an EvidenceAssessment by canonical ID with case clearance enforcement."""
        raw = self._repo.get_evidence_assessment(str(assessment_id))
        if not raw:
            return None

        assessment = EvidenceAssessment(**raw)
        if principal and self._auth:
            allowed, _reason = self._auth.can_access_case(principal, assessment.case_id)
            if not allowed:
                raise PermissionError(f"Access denied: cannot view assessment for case '{assessment.case_id}'")

        return assessment

    def list_assessments(
        self,
        case_id: str | None = None,
        state: EpistemicState | None = None,
        entity_id: str | None = None,
        edge_id: str | None = None,
        claim_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        principal: Principal | None = None,
    ) -> EvidenceAssessmentListResponse:
        """Query and filter assessments, filtering out cases unauthorized for the principal."""
        state_str = state.value if state else None
        raw_items, total = self._repo.list_evidence_assessments(
            case_id=case_id,
            state=state_str,
            entity_id=entity_id,
            edge_id=edge_id,
            claim_type=claim_type,
            limit=limit,
            offset=offset,
        )

        assessments: list[EvidenceAssessment] = []
        for item in raw_items:
            asmt = EvidenceAssessment(**item)
            if principal and self._auth:
                allowed, _ = self._auth.can_access_case(principal, asmt.case_id)
                if not allowed:
                    continue
            assessments.append(asmt)

        return EvidenceAssessmentListResponse(
            assessments=assessments,
            total_count=total if not (principal and self._auth) else len(assessments),
            case_id=case_id,
            state=state,
            limit=limit,
            offset=offset,
        )

    # ── Pulse Compatibility Helper ────────────────────────────────────────────

    def to_pulse_item(self, assessment: EvidenceAssessment) -> EvidenceAssessmentItem:
        """Project a domain EvidenceAssessment into a backward-compatible pulse item."""
        return assessment.to_pulse_item()
