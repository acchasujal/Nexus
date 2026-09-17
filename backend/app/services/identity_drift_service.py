"""backend/app/services/identity_drift_service.py

Identity Drift Radar Service for NEXUS (P1-B).
Provides:
  - Detection of carrier switching, burner SIM turnover, device hopping, vehicle drift, and alias evolution.
  - Integration with GraphStore and Ingestion records.
  - Officer decision tracking (CONFIRMED, DISMISSED, MONITORING) with note and timestamp.
  - Zero predictive guilt bias: strictly tracks operational communication/identity transitions.
  - Cryptographic audit trail on detection queries and officer actions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.graph.algorithms.identity_drift import detect_identity_drifts_in_store
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    DecideIdentityDriftRequest,
    IdentityDriftEvent,
    IdentityDriftStatus,
    IdentityDriftType,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdentityDriftService:
    """Application-layer service managing the lifecycle of Identity Drift Radar findings."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        audit_service: AuditService,
    ) -> None:
        self.repo = repository
        self.audit = audit_service
        self._initialize_baseline_drift_events()

    def _initialize_baseline_drift_events(self) -> None:
        """Seed baseline identity drift events for golden entities (e.g. Rafiq Khan, Deepak Rao)."""
        if getattr(self.repo, "identity_drifts", None) is None:
            self.repo.identity_drifts = {}

        if self.repo.identity_drifts:
            return

        # Canonical baseline drift #1: Rafiq Khan burner phone turnover
        rafiq_drift = IdentityDriftEvent(
            drift_id="DRIFT-2026-PH-RAFIQ",
            person_id="P-RAFIQ",
            person_name="Rafiq Khan",
            drift_type=IdentityDriftType.PHONE_TURNOVER,
            previous_value="+91 98450 11223",
            new_value="+91 98450 99881",
            previous_seen_at="2026-02-11T09:30:00Z",
            new_seen_at="2026-03-02T14:15:00Z",
            time_window_days=19,
            corroborating_context=(
                "Burner SIM turnover: Primary communication line ceased activity on 2026-02-11 following FIR-141. "
                "Target reactivated on secondary subscriber line +91 98450 99881 within 19 days."
            ),
            evidence_refs=["SRC-FIR-141", "SRC-CDR-A12", "SRC-CDR-B31"],
            derivation_class="DERIVED",
            human_status=IdentityDriftStatus.DETECTED,
        )
        self.repo.identity_drifts[rafiq_drift.drift_id] = rafiq_drift.model_dump()

        # Canonical baseline drift #2: Deepak Rao device hopping
        deepak_drift = IdentityDriftEvent(
            drift_id="DRIFT-2026-DEV-DEEPAK",
            person_id="P-DEEPAK",
            person_name="Deepak Rao",
            drift_type=IdentityDriftType.DEVICE_HOP,
            previous_value="IMEI 861234567890123",
            new_value="IMEI 869876543210987",
            previous_seen_at="2026-02-18T11:00:00Z",
            new_seen_at="2026-03-05T16:30:00Z",
            time_window_days=15,
            corroborating_context=(
                "Handset swap: Switch records show SIM +91 98450 99881 moved from IMEI 861234567890123 "
                "to newly provisioned device IMEI 869876543210987."
            ),
            evidence_refs=["SRC-CDR-B31", "SRC-FIR-207"],
            derivation_class="DERIVED",
            human_status=IdentityDriftStatus.DETECTED,
        )
        self.repo.identity_drifts[deepak_drift.drift_id] = deepak_drift.model_dump()

        # Canonical baseline drift #3: Bikram Sarma / Vikram Sharma alias evolution
        alias_drift = IdentityDriftEvent(
            drift_id="DRIFT-2026-ALIAS-VIKRAM",
            person_id="person-0001",
            person_name="Vikram Sharma",
            drift_type=IdentityDriftType.ALIAS_EVOLUTION,
            previous_value="Vicky",
            new_value="Doctor",
            previous_seen_at="2026-01-20T10:00:00Z",
            new_seen_at="2026-02-28T12:00:00Z",
            time_window_days=39,
            corroborating_context=(
                "Operational moniker transition: Subject initially cited as 'Vicky' in Mysuru jurisdiction, "
                "subsequently operating under moniker 'Doctor' in cyber syndicate filings."
            ),
            evidence_refs=["SRC-FIR-141", "SRC-FIR-207"],
            derivation_class="DERIVED",
            human_status=IdentityDriftStatus.CONFIRMED,
            decided_at="2026-03-06T09:00:00Z",
            decided_by="IO Rajesh Kumar (BADGE-IO-412)",
            investigator_note="Corroborated across both Bengaluru and Mysuru charge-sheets.",
        )
        self.repo.identity_drifts[alias_drift.drift_id] = alias_drift.model_dump()

    def list_identity_drifts(
        self,
        principal: Principal | None = None,
        person_id: str | None = None,
        drift_type: IdentityDriftType | None = None,
        status: IdentityDriftStatus | None = None,
    ) -> list[IdentityDriftEvent]:
        """
        List all detected and persisted identity drift events.
        Merges dynamic graph traversal results with saved decisions.
        """
        # 1. Run dynamic detection across graph store
        store = self.repo.to_graph_store()
        dynamic_drifts = detect_identity_drifts_in_store(store, person_id_filter=person_id)

        # 2. Merge with persisted repository state (so investigator decisions persist)
        merged: dict[str, IdentityDriftEvent] = {}

        # First add seeded / saved records
        for d_id, raw in self.repo.identity_drifts.items():
            ev = IdentityDriftEvent(**raw)
            if person_id and ev.person_id != person_id:
                continue
            merged[d_id] = ev

        # Overlay dynamically detected drifts (preserving existing status/notes if already decided)
        for d in dynamic_drifts:
            if d.drift_id in merged:
                # Keep decision fields from persisted record
                persisted = merged[d.drift_id]
                d.human_status = persisted.human_status
                d.investigator_note = persisted.investigator_note
                d.decided_at = persisted.decided_at
                d.decided_by = persisted.decided_by
            else:
                self.repo.identity_drifts[d.drift_id] = d.model_dump()
            merged[d.drift_id] = d

        results = list(merged.values())

        # Filter by type & status
        if drift_type:
            results = [r for r in results if r.drift_type == drift_type]
        if status:
            results = [r for r in results if r.human_status == status]

        # Deterministic sorting
        results.sort(key=lambda x: (x.human_status.value, x.drift_type.value, x.person_name, x.drift_id))

        if principal:
            self.audit.record(
                event_type=AuditEventType.IDENTITY_DRIFT_VIEWED,
                actor_id=principal.user_id,
                details={"action": "LIST_IDENTITY_DRIFTS", "count": len(results)},
            )

        return results

    def decide_identity_drift(
        self,
        drift_id: str,
        request: DecideIdentityDriftRequest,
        principal: Principal,
    ) -> IdentityDriftEvent:
        """
        Authoritatively record an investigator decision on a drift event.
        Writes immutable audit log.
        """
        if drift_id not in self.repo.identity_drifts:
            # Check dynamic pool
            store = self.repo.to_graph_store()
            dyn = detect_identity_drifts_in_store(store)
            found = next((d for d in dyn if d.drift_id == drift_id), None)
            if not found:
                raise KeyError(f"Identity drift event '{drift_id}' not found.")
            self.repo.identity_drifts[drift_id] = found.model_dump()

        raw = self.repo.identity_drifts[drift_id]
        event = IdentityDriftEvent(**raw)

        officer = principal.get_officer_identity()
        decided_by_str = f"{officer.name} ({officer.badge_number})" if officer.badge_number else (officer.name or principal.user_id)

        event.human_status = request.status
        event.investigator_note = request.note
        event.decided_at = _utcnow().isoformat()
        event.decided_by = decided_by_str

        self.repo.identity_drifts[drift_id] = event.model_dump()

        self.audit.record(
            event_type=AuditEventType.IDENTITY_DRIFT_DECIDED,
            actor_id=principal.user_id,
            entity_id=drift_id,
            entity_type="IdentityDriftEvent",
            details={
                "action": "DECIDE_IDENTITY_DRIFT",
                "status": request.status.value,
                "note": request.note,
                "decided_by": decided_by_str,
                "person_id": event.person_id,
            },
        )

        return event

    def get_drift_radar_summary(self) -> dict[str, Any]:
        """Provide aggregated metrics for the Identity Drift Radar dashboard."""
        drifts = self.list_identity_drifts()

        by_type: dict[str, int] = {}
        for d in drifts:
            by_type[d.drift_type.value] = by_type.get(d.drift_type.value, 0) + 1

        by_status: dict[str, int] = {}
        for d in drifts:
            by_status[d.human_status.value] = by_status.get(d.human_status.value, 0) + 1

        return {
            "total_drifts": len(drifts),
            "by_type": by_type,
            "by_status": by_status,
            "phone_turnovers": by_type.get(IdentityDriftType.PHONE_TURNOVER.value, 0),
            "device_hops": by_type.get(IdentityDriftType.DEVICE_HOP.value, 0),
            "vehicle_drifts": by_type.get(IdentityDriftType.VEHICLE_DRIFT.value, 0),
            "alias_evolutions": by_type.get(IdentityDriftType.ALIAS_EVOLUTION.value, 0),
            "active_monitoring": by_status.get(IdentityDriftStatus.MONITORING.value, 0),
            "confirmed_drifts": by_status.get(IdentityDriftStatus.CONFIRMED.value, 0),
        }
