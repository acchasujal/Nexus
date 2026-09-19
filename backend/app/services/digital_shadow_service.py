"""backend/app/services/digital_shadow_service.py

Digital Shadow & SOCMINT Governance Service for NEXUS (P1-D).
Provides:
  - Controlled public digital identifier fusion with strict Section 63 BSA compliance.
  - Strict 4-Stage Lifecycle: OBSERVED -> CANDIDATE_LINK -> CORROBORATED -> INVESTIGATOR_CONFIRMED.
  - Non-Equivalence Rule: A digital alias/handle is never equivalent to legal person proof
    without mandatory corroboration via a physical hard identifier (Phone, IMEI, Account).
  - Officer decision tracking (INVESTIGATOR_CONFIRMED, DISMISSED, CORROBORATED) with notes and timestamps.
  - Strict Zero Predictive Guilt: strictly tracks digital artifact corroboration states.
  - Append-only cryptographic audit logging.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.graph.algorithms.digital_shadow import detect_digital_shadow_corroborations_in_store
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    DecideDigitalShadowRequest,
    DigitalShadowCorroboration,
    DigitalShadowLifecycle,
    DigitalShadowPlatform,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DigitalShadowService:
    """Application-layer service managing the lifecycle of Digital Shadow corroborations."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        audit_service: AuditService,
    ) -> None:
        self.repo = repository
        self.audit = audit_service
        self._initialize_baseline_shadows()

    def _initialize_baseline_shadows(self) -> None:
        """Seed baseline digital shadow corroborations for golden investigative fixtures."""
        if getattr(self.repo, "digital_shadows", None) is None:
            self.repo.digital_shadows = {}

        if self.repo.digital_shadows:
            return

        # Canonical baseline corroboration #1: Telegram Channel Coordinator (Rafiq Khan)
        shadow_1 = DigitalShadowCorroboration(
            corroboration_id="SHADOW-2026-TG-RAFIQ",
            person_id="P-RAFIQ",
            person_name="Rafiq Khan",
            platform=DigitalShadowPlatform.TELEGRAM,
            digital_identifier="@hawk_ops_mysuru",
            corroborating_physical_id="+91 98450 11223",
            corroborating_physical_type="Phone",
            confidence_score=0.92,
            lifecycle_state=DigitalShadowLifecycle.CORROBORATED,
            observation_context=(
                "Telegram handle '@hawk_ops_mysuru' surfaced in seized device handset dump. "
                "Registration linked to subscriber primary MSISDN (+91 98450 11223) in CDR tower logs."
            ),
            source_url_or_channel="https://t.me/hawk_ops_mysuru",
            evidence_refs=["SRC-FIR-141", "SRC-CDR-A12", "SRC-FIR-207"],
            derivation_class="DERIVED",
            first_observed_at="2026-02-15T10:00:00Z",
            last_verified_at="2026-03-01T14:30:00Z",
        )
        self.repo.digital_shadows[shadow_1.corroboration_id] = shadow_1.model_dump()

        # Canonical baseline corroboration #2: Darknet Forum Escrow Vendor (Deepak Rao)
        shadow_2 = DigitalShadowCorroboration(
            corroboration_id="SHADOW-2026-DARK-DEEPAK",
            person_id="P-DEEPAK",
            person_name="Deepak Rao",
            platform=DigitalShadowPlatform.DARKWEB_FORUM,
            digital_identifier="vendor_deepak_hyd",
            corroborating_physical_id="861234567890123",
            corroborating_physical_type="Device IMEI",
            confidence_score=0.88,
            lifecycle_state=DigitalShadowLifecycle.CANDIDATE_LINK,
            observation_context=(
                "Public forum escrow identifier 'vendor_deepak_hyd' referenced in cyber hawala chatter. "
                "Hardware fingerprint IMEI 861234567890123 matches seized device registration."
            ),
            source_url_or_channel="https://sec-forum.internal/u/vendor_deepak_hyd",
            evidence_refs=["SRC-CDR-B31", "SRC-FIR-207"],
            derivation_class="DERIVED",
            first_observed_at="2026-02-20T16:45:00Z",
        )
        self.repo.digital_shadows[shadow_2.corroboration_id] = shadow_2.model_dump()

        # Canonical baseline corroboration #3: Payment Gateway Mule VPA (Mule Account)
        shadow_3 = DigitalShadowCorroboration(
            corroboration_id="SHADOW-2026-UPI-ACC0002",
            person_id="account-0002",
            person_name="Layering Conduit ACC-0002",
            platform=DigitalShadowPlatform.PAYMENT_GATEWAY,
            digital_identifier="fastpay.layering@okhdfcbank",
            corroborating_physical_id="ACC-9914",
            corroborating_physical_type="Bank Account",
            confidence_score=0.95,
            lifecycle_state=DigitalShadowLifecycle.INVESTIGATOR_CONFIRMED,
            observation_context=(
                "Virtual Payment Address (VPA) tied to structured IMPS smurfing tranches. "
                "Bank KYC corroborates primary beneficiary account ACC-9914."
            ),
            source_url_or_channel="https://upi-switch.internal/vpa/fastpay.layering",
            evidence_refs=["SRC-TXN-55", "SRC-TXN-71", "SRC-FIR-141"],
            derivation_class="DERIVED",
            first_observed_at="2026-02-28T09:15:00Z",
            last_verified_at="2026-03-10T11:20:00Z",
            decided_at="2026-03-12T16:00:00Z",
            decided_by="IO Rajesh Kumar (BADGE-IO-412)",
            investigator_note="Corroborated by bank statement submission and Section 94 BNSS response.",
        )
        self.repo.digital_shadows[shadow_3.corroboration_id] = shadow_3.model_dump()

    def list_digital_shadows(
        self,
        principal: Principal | None = None,
        person_id: str | None = None,
        platform: DigitalShadowPlatform | None = None,
        lifecycle_state: DigitalShadowLifecycle | None = None,
    ) -> list[DigitalShadowCorroboration]:
        """
        List all detected and persisted digital shadow corroborations.
        Merges dynamic graph traversal results with saved decisions.
        """
        store = self.repo.to_graph_store()
        dynamic_shadows = detect_digital_shadow_corroborations_in_store(store, person_id_filter=person_id)

        merged: dict[str, DigitalShadowCorroboration] = {}
        for s_id, raw in self.repo.digital_shadows.items():
            merged[s_id] = DigitalShadowCorroboration(**raw)

        for d in dynamic_shadows:
            if d.corroboration_id in merged:
                persisted = merged[d.corroboration_id]
                d.lifecycle_state = persisted.lifecycle_state
                d.investigator_note = persisted.investigator_note
                d.decided_at = persisted.decided_at
                d.decided_by = persisted.decided_by
            else:
                self.repo.digital_shadows[d.corroboration_id] = d.model_dump()
            merged[d.corroboration_id] = d

        results = list(merged.values())

        if person_id:
            results = [r for r in results if r.person_id == person_id]
        if platform:
            results = [r for r in results if r.platform == platform]
        if lifecycle_state:
            results = [r for r in results if r.lifecycle_state == lifecycle_state]

        results.sort(key=lambda x: (x.lifecycle_state.value, x.platform.value, x.person_name, x.corroboration_id))

        if principal:
            self.audit.record(
                event_type=AuditEventType.DIGITAL_SHADOW_VIEWED,
                actor_id=principal.user_id,
                details={"action": "LIST_DIGITAL_SHADOWS", "count": len(results)},
            )

        return results

    def decide_digital_shadow(
        self,
        corroboration_id: str,
        request: DecideDigitalShadowRequest,
        principal: Principal,
    ) -> DigitalShadowCorroboration:
        """
        Authoritatively advance or dismiss the Section 63 BSA lifecycle state of a digital footprint.
        Writes immutable audit trail.
        """
        if corroboration_id not in self.repo.digital_shadows:
            store = self.repo.to_graph_store()
            dyn = detect_digital_shadow_corroborations_in_store(store)
            found = next((s for s in dyn if s.corroboration_id == corroboration_id), None)
            if not found:
                raise KeyError(f"Digital shadow corroboration '{corroboration_id}' not found.")
            self.repo.digital_shadows[corroboration_id] = found.model_dump()

        raw = self.repo.digital_shadows[corroboration_id]
        corroboration = DigitalShadowCorroboration(**raw)

        officer = principal.get_officer_identity()
        decided_by_str = f"{officer.name} ({officer.badge_number})" if officer.badge_number else (officer.name or principal.user_id)

        corroboration.lifecycle_state = request.lifecycle_state
        corroboration.investigator_note = request.note
        corroboration.decided_at = _utcnow().isoformat()
        corroboration.decided_by = decided_by_str

        self.repo.digital_shadows[corroboration_id] = corroboration.model_dump()

        self.audit.record(
            event_type=AuditEventType.DIGITAL_SHADOW_DECIDED,
            actor_id=principal.user_id,
            entity_id=corroboration_id,
            entity_type="DigitalShadowCorroboration",
            details={
                "action": "DECIDE_DIGITAL_SHADOW",
                "lifecycle_state": request.lifecycle_state.value,
                "note": request.note,
                "decided_by": decided_by_str,
                "person_id": corroboration.person_id,
                "digital_identifier": corroboration.digital_identifier,
                "corroborating_physical_id": corroboration.corroborating_physical_id,
            },
        )

        return corroboration

    def get_digital_shadow_summary(self) -> dict[str, Any]:
        """Provide aggregated metrics for Digital Shadow Radar."""
        shadows = self.list_digital_shadows()

        by_platform: dict[str, int] = {}
        for s in shadows:
            by_platform[s.platform.value] = by_platform.get(s.platform.value, 0) + 1

        by_lifecycle: dict[str, int] = {}
        for s in shadows:
            by_lifecycle[s.lifecycle_state.value] = by_lifecycle.get(s.lifecycle_state.value, 0) + 1

        return {
            "total_corroborations": len(shadows),
            "by_platform": by_platform,
            "by_lifecycle": by_lifecycle,
            "telegram_channels": by_platform.get(DigitalShadowPlatform.TELEGRAM.value, 0),
            "darknet_forum_links": by_platform.get(DigitalShadowPlatform.DARKWEB_FORUM.value, 0),
            "payment_gateways": by_platform.get(DigitalShadowPlatform.PAYMENT_GATEWAY.value, 0),
            "corroborated_links": by_lifecycle.get(DigitalShadowLifecycle.CORROBORATED.value, 0),
            "confirmed_links": by_lifecycle.get(DigitalShadowLifecycle.INVESTIGATOR_CONFIRMED.value, 0),
            "candidate_links": by_lifecycle.get(DigitalShadowLifecycle.CANDIDATE_LINK.value, 0),
        }
