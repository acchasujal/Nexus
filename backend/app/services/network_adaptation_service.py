"""backend/app/services/network_adaptation_service.py

Network Adaptation Service for NEXUS (P1-C).
Provides:
  - Detection of intermediary replacement, bridge substitution, financial rerouting, and community reconnection.
  - Integration with GraphStore and temporal investigative snapshots.
  - Officer decision tracking (CONFIRMED, DISMISSED, MONITORING) with note and timestamp.
  - Strict zero predictive guilt bias: strictly analyzes topological structural reconfigurations.
  - Cryptographic audit trail on inspection and decision events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.graph.algorithms.network_adaptation import detect_network_adaptations_in_store
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    AdaptationReviewStatus,
    DecideNetworkAdaptationRequest,
    NetworkAdaptationEvent,
    NetworkAdaptationType,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NetworkAdaptationService:
    """Application-layer service managing the lifecycle of Network Adaptation findings."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        audit_service: AuditService,
    ) -> None:
        self.repo = repository
        self.audit = audit_service
        self._initialize_baseline_adaptations()

    def _initialize_baseline_adaptations(self) -> None:
        """Seed baseline network adaptation events for golden investigative fixtures."""
        if getattr(self.repo, "network_adaptations", None) is None:
            self.repo.network_adaptations = {}

        if self.repo.network_adaptations:
            return

        # Canonical baseline adaptation #1: Intermediary Proxy Replacement (Rafiq Khan -> Proxy -> Deepak Rao)
        proxy_event = NetworkAdaptationEvent(
            adaptation_id="ADAPT-2026-PROXY-RAFIQ-DEEPAK",
            adaptation_type=NetworkAdaptationType.INTERMEDIARY_REPLACEMENT,
            primary_entity_id="P-RAFIQ",
            primary_entity_name="Rafiq Khan",
            secondary_entity_id="P-DEEPAK",
            secondary_entity_name="Deepak Rao",
            substitute_intermediary_id="person-0003",
            substitute_intermediary_name="V. Sharma (Proxy Broker)",
            previous_path=["P-RAFIQ", "P-DEEPAK"],
            new_path=["P-RAFIQ", "person-0003", "P-DEEPAK"],
            detected_at="2026-03-05T14:00:00Z",
            time_lag_days=12,
            structural_significance=0.91,
            corroborating_context=(
                "Intermediary replacement: Direct CDR communication link between Rafiq Khan and Deepak Rao ceased "
                "post FIR-141. Active multi-hop coordination conduit re-emerged through proxy conduit V. Sharma."
            ),
            evidence_refs=["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31"],
            derivation_class="DERIVED",
            review_status=AdaptationReviewStatus.DETECTED,
        )
        self.repo.network_adaptations[proxy_event.adaptation_id] = proxy_event.model_dump()

        # Canonical baseline adaptation #2: Cross-Syndicate Bridge Substitution
        bridge_event = NetworkAdaptationEvent(
            adaptation_id="ADAPT-2026-BRIDGE-SUBSTITUTION",
            adaptation_type=NetworkAdaptationType.BRIDGE_SUBSTITUTION,
            primary_entity_id="person-0051",
            primary_entity_name="Ramesh Hegde (Broker)",
            secondary_entity_id="COMM-BETA",
            secondary_entity_name="Cyber Hawala Syndicate",
            substitute_intermediary_id="person-0051",
            substitute_intermediary_name="Ramesh Hegde",
            previous_path=["FORMER-CONNECTOR-01", "COMM-BETA"],
            new_path=["person-0051", "COMM-BETA"],
            detected_at="2026-03-08T09:30:00Z",
            time_lag_days=9,
            structural_significance=0.88,
            corroborating_context=(
                "Bridge broker substitution: Betweenness centrality analysis detects Ramesh Hegde assuming "
                "inter-syndicate coordination role connecting Coastal Narcotics and Cyber Hawala syndicates."
            ),
            evidence_refs=["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-BRIDGE-01", "SRC-CDR-BRIDGE-02"],
            derivation_class="DERIVED",
            review_status=AdaptationReviewStatus.CONFIRMED,
            decided_at="2026-03-12T11:00:00Z",
            decided_by="IO Rajesh Kumar (BADGE-IO-412)",
            investigator_note="Corroborated by joint Mysuru-Bengaluru CDR tower data.",
        )
        self.repo.network_adaptations[bridge_event.adaptation_id] = bridge_event.model_dump()

        # Canonical baseline adaptation #3: Financial Transaction Rerouting (Smurfing Layer)
        financial_event = NetworkAdaptationEvent(
            adaptation_id="ADAPT-2026-FINANCIAL-REROUTE",
            adaptation_type=NetworkAdaptationType.FINANCIAL_REROUTING,
            primary_entity_id="ACC-7731",
            primary_entity_name="Mule Account ACC-7731",
            secondary_entity_id="ACC-9914",
            secondary_entity_name="Mule Account ACC-9914",
            substitute_intermediary_id="account-0002",
            substitute_intermediary_name="Layering Conduit ACC-0002",
            previous_path=["ACC-7731", "ACC-9914"],
            new_path=["ACC-7731", "account-0002", "ACC-9914"],
            detected_at="2026-03-07T16:15:00Z",
            time_lag_days=7,
            structural_significance=0.94,
            corroborating_context=(
                "Financial route transition: Direct RTGS flow between primary accounts frozen; "
                "transfers rerouted via structured micro-smurfing IMPS tranches through intermediary account."
            ),
            evidence_refs=["SRC-TXN-55", "SRC-TXN-71", "SRC-FIR-141"],
            derivation_class="DERIVED",
            review_status=AdaptationReviewStatus.MONITORING,
            decided_at="2026-03-14T15:30:00Z",
            decided_by="Analyst Suresh Babu (BADGE-AN-108)",
            investigator_note="Notice served under Section 94 BNSS for bank KYC logs.",
        )
        self.repo.network_adaptations[financial_event.adaptation_id] = financial_event.model_dump()

    def list_adaptations(
        self,
        principal: Principal | None = None,
        adaptation_type: NetworkAdaptationType | None = None,
        status: AdaptationReviewStatus | None = None,
    ) -> list[NetworkAdaptationEvent]:
        """
        List all detected and persisted network adaptation events.
        Merges dynamic graph traversal results with saved decisions.
        """
        # 1. Run dynamic detection across graph store
        store = self.repo.to_graph_store()
        dynamic_adaptations = detect_network_adaptations_in_store(store)

        # 2. Merge with persisted repository state (so decisions persist)
        merged: dict[str, NetworkAdaptationEvent] = {}

        for a_id, raw in self.repo.network_adaptations.items():
            merged[a_id] = NetworkAdaptationEvent(**raw)

        for d in dynamic_adaptations:
            if d.adaptation_id in merged:
                persisted = merged[d.adaptation_id]
                d.review_status = persisted.review_status
                d.investigator_note = persisted.investigator_note
                d.decided_at = persisted.decided_at
                d.decided_by = persisted.decided_by
            else:
                self.repo.network_adaptations[d.adaptation_id] = d.model_dump()
            merged[d.adaptation_id] = d

        results = list(merged.values())

        if adaptation_type:
            results = [r for r in results if r.adaptation_type == adaptation_type]
        if status:
            results = [r for r in results if r.review_status == status]

        results.sort(key=lambda x: (x.review_status.value, x.adaptation_type.value, x.primary_entity_name, x.adaptation_id))

        if principal:
            self.audit.record(
                event_type=AuditEventType.NETWORK_ADAPTATION_VIEWED,
                actor_id=principal.user_id,
                details={"action": "LIST_NETWORK_ADAPTATIONS", "count": len(results)},
            )

        return results

    def decide_adaptation(
        self,
        adaptation_id: str,
        request: DecideNetworkAdaptationRequest,
        principal: Principal,
    ) -> NetworkAdaptationEvent:
        """
        Authoritatively record an investigator decision on a network adaptation event.
        Writes immutable audit trail.
        """
        if adaptation_id not in self.repo.network_adaptations:
            store = self.repo.to_graph_store()
            dyn = detect_network_adaptations_in_store(store)
            found = next((a for a in dyn if a.adaptation_id == adaptation_id), None)
            if not found:
                raise KeyError(f"Network adaptation event '{adaptation_id}' not found.")
            self.repo.network_adaptations[adaptation_id] = found.model_dump()

        raw = self.repo.network_adaptations[adaptation_id]
        event = NetworkAdaptationEvent(**raw)

        officer = principal.get_officer_identity()
        decided_by_str = f"{officer.name} ({officer.badge_number})" if officer.badge_number else (officer.name or principal.user_id)

        event.review_status = request.status
        event.investigator_note = request.note
        event.decided_at = _utcnow().isoformat()
        event.decided_by = decided_by_str

        self.repo.network_adaptations[adaptation_id] = event.model_dump()

        self.audit.record(
            event_type=AuditEventType.NETWORK_ADAPTATION_DECIDED,
            actor_id=principal.user_id,
            entity_id=adaptation_id,
            entity_type="NetworkAdaptationEvent",
            details={
                "action": "DECIDE_NETWORK_ADAPTATION",
                "status": request.status.value,
                "note": request.note,
                "decided_by": decided_by_str,
                "primary_entity_id": event.primary_entity_id,
                "secondary_entity_id": event.secondary_entity_id,
            },
        )

        return event

    def get_adaptation_radar_summary(self) -> dict[str, Any]:
        """Provide aggregated metrics for Network Adaptation Radar."""
        adaptations = self.list_adaptations()

        by_type: dict[str, int] = {}
        for a in adaptations:
            by_type[a.adaptation_type.value] = by_type.get(a.adaptation_type.value, 0) + 1

        by_status: dict[str, int] = {}
        for a in adaptations:
            by_status[a.review_status.value] = by_status.get(a.review_status.value, 0) + 1

        return {
            "total_adaptations": len(adaptations),
            "by_type": by_type,
            "by_status": by_status,
            "intermediary_replacements": by_type.get(NetworkAdaptationType.INTERMEDIARY_REPLACEMENT.value, 0),
            "bridge_substitutions": by_type.get(NetworkAdaptationType.BRIDGE_SUBSTITUTION.value, 0),
            "financial_reroutings": by_type.get(NetworkAdaptationType.FINANCIAL_REROUTING.value, 0),
            "community_reconnections": by_type.get(NetworkAdaptationType.COMMUNITY_RECONNECTION.value, 0),
            "active_monitoring": by_status.get(AdaptationReviewStatus.MONITORING.value, 0),
            "confirmed_adaptations": by_status.get(AdaptationReviewStatus.CONFIRMED.value, 0),
        }
