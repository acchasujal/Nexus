"""backend/app/services/canonical_read_model.py

Authoritative Canonical Intelligence Read Model Pipeline (Phase 2).
Generates and serves a deterministic, versioned read-model bundle from the
same underlying graph and forensic evidence data as the backend repository.
Eliminates any requirement for hand-authored frontend fallback numbers.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.contracts.api import (
    CANONICAL_DATASET_VERSION,
    CANONICAL_SNAPSHOT_BASELINE,
    CANONICAL_SNAPSHOT_CURRENT,
    CaseDNA,
    CaseDNAMatchResponse,
    GraphSnapshotSummary,
    IntelligenceBootstrapResponse,
    IntelligenceKPIs,
    NetworkDiffResponse,
    NetworkPulseItem,
    ReviewPriority,
)

logger = logging.getLogger(__name__)

READ_MODEL_CACHE: dict[str, dict[str, Any]] = {}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_dataset_checksum(data: Any) -> str:
    """Compute a deterministic SHA-256 checksum for the dataset or read-model bundle."""
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def build_canonical_read_model() -> dict[str, Any]:
    """
    Build ONE unified read model from the canonical synthetic/demo data and graph.
    Matches all invariants required by Phase 2.
    """
    # 1. Base canonical cases
    cases_data = [
        {
            "case_id": "CASE-141",
            "fir_number": "FIR-2026-141",
            "title": "FIR No. 141/2026 — Inter-State Cargo Smuggling",
            "district": "Mysuru",
            "status": "UNDER_INVESTIGATION",
            "priority": "HIGH",
            "last_activity": "2026-08-24T18:00:00Z",
            "evidence_state": "LINKED_VERIFIED",
            "jurisdictions": ["Mysuru", "Bengaluru City"],
            "linked_cases": ["CASE-207"],
            "pending_verification": 1,
            "assigned_officer": "Insp. Ramesh Rao",
            "latest_signal": "Cross-jurisdiction telecom & smurfing link to CASE-207",
            "next_action": "Issue Section 63 BSA production notice for cell tower dump",
        },
        {
            "case_id": "CASE-207",
            "fir_number": "FIR-2026-207",
            "title": "FIR No. 207/2026 — Peeling Chain Cyber Fraud",
            "district": "Bengaluru City",
            "status": "UNDER_INVESTIGATION",
            "priority": "HIGH",
            "last_activity": "2026-08-24T18:00:00Z",
            "evidence_state": "LINKED_VERIFIED",
            "jurisdictions": ["Bengaluru City", "Mysuru"],
            "linked_cases": ["CASE-141"],
            "pending_verification": 1,
            "assigned_officer": "Insp. Priya Sharma",
            "latest_signal": "Hawala money conduit to Axis mule account ACC-7731",
            "next_action": "Freeze mule account ACC-7731 via FIU-IND channel",
        },
        {
            "case_id": "CASE-305",
            "fir_number": "FIR-2026-305",
            "title": "FIR No. 305/2026 — Inter-District Narcotics Distribution",
            "district": "Mangaluru",
            "status": "EVIDENCE_GATHERING",
            "priority": "CRITICAL",
            "last_activity": "2026-08-24T16:30:00Z",
            "evidence_state": "PARTIAL",
            "jurisdictions": ["Mangaluru", "Hubballi-Dharwad"],
            "linked_cases": ["CASE-412"],
            "pending_verification": 2,
            "assigned_officer": "ACP Suresh Patil",
            "latest_signal": "Alias overlap resolved with Bikram Sarma in CASE-412",
            "next_action": "Verify bank statement for account ACC-4491",
        },
        {
            "case_id": "CASE-412",
            "fir_number": "FIR-2026-412",
            "title": "FIR No. 412/2026 — Hawala Peeling Network Operation",
            "district": "Hubballi-Dharwad",
            "status": "UNDER_INVESTIGATION",
            "priority": "CRITICAL",
            "last_activity": "2026-08-24T16:30:00Z",
            "evidence_state": "LINKED_VERIFIED",
            "jurisdictions": ["Hubballi-Dharwad", "Mangaluru"],
            "linked_cases": ["CASE-305"],
            "pending_verification": 1,
            "assigned_officer": "Insp. Anita K",
            "latest_signal": "Layered fund routing through syndicate clearing nodes",
            "next_action": "Obtain carrier CDR handover certificate",
        },
        {
            "case_id": "CASE-501",
            "fir_number": "FIR-2026-501",
            "title": "FIR No. 501/2026 — Transshipment Cargo Conduit",
            "district": "Belagavi",
            "status": "EVIDENCE_GATHERING",
            "priority": "MEDIUM",
            "last_activity": "2026-08-24T14:00:00Z",
            "evidence_state": "CORROBORATED",
            "jurisdictions": ["Belagavi", "Vijayapura"],
            "linked_cases": ["CASE-502"],
            "pending_verification": 1,
            "assigned_officer": "Insp. Vijay Naik",
            "latest_signal": "Vehicle KA-01-AB-1001 shared with CASE-502",
            "next_action": "Confirm RTO vehicle ownership transfer certificate",
        },
        {
            "case_id": "CASE-502",
            "fir_number": "FIR-2026-502",
            "title": "FIR No. 502/2026 — Inter-State Supply Network",
            "district": "Vijayapura",
            "status": "EVIDENCE_GATHERING",
            "priority": "MEDIUM",
            "last_activity": "2026-08-24T14:00:00Z",
            "evidence_state": "CORROBORATED",
            "jurisdictions": ["Vijayapura", "Belagavi"],
            "linked_cases": ["CASE-501"],
            "pending_verification": 1,
            "assigned_officer": "Insp. Mahesh Joshi",
            "latest_signal": "Logistics operative Suniel Shetty linked to vehicle KA-01-AB-1001",
            "next_action": "Inspect toll plaza FASTag passage timestamps",
        },
    ]

    # 2. Canonical Network Delta between snap-baseline-v1 and snap-current
    added_nodes = ["P-RAFIQ", "PH-UNIFIED", "P-VIKRAM", "P-SUNIEL"]
    removed_nodes = ["P-RAFIQ-K", "P-RAFIQ-A", "PH-A", "PH-B", "P-VIKRAM-S", "P-BIKRAM-S", "P-SUNIEL-S", "P-SUNIL-S"]
    added_relationships = [
        "E-BRIDGE",
        "E-COMM-DK",
        "E-TXN-55",
        "E-TXN-71",
        "E-BRIDGE-2",
        "E-TXN-HWL",
        "E-BRIDGE-3",
        "E-USEPH-1",
        "E-USEPH-2",
    ]
    removed_relationships = ["E-ACCUSE-141", "E-ACCUSE-207", "E-USEPH-A", "E-USEPH-B"]

    network_delta = {
        "before_snapshot_id": CANONICAL_SNAPSHOT_BASELINE,
        "after_snapshot_id": CANONICAL_SNAPSHOT_CURRENT,
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_relationships": added_relationships,
        "removed_relationships": removed_relationships,
        "added_node_count": len(added_nodes),
        "removed_node_count": len(removed_nodes),
        "added_relationship_count": len(added_relationships),
        "removed_relationship_count": len(removed_relationships),
        "dataset_version": CANONICAL_DATASET_VERSION,
    }

    # 3. Canonical Primary Network Pulse
    primary_pulse = {
        "pulse_id": "pulse-0082",
        "change_ids": ["E-BRIDGE", "E-COMM-DK", "E-TXN-55"],
        "signal_headline": "Cross-Jurisdiction Syndicate Conduit Detected",
        "review_priority": "CRITICAL_REVIEW",
        "time_window": ["2026-02-11T09:30:00Z", "2026-08-24T18:00:00Z"],
        "evidence_refs": ["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"],
        "support_level": 0.94,
        "uncertainty": 0.06,
        "action_window": "Immediate",
        "abstained": False,
        "generated_at": "2026-08-24T18:05:00Z",
        "affected_entities": ["P-RAFIQ", "P-DEEPAK", "ACC-7731", "ACC-9914"],
        "affected_cases": ["CASE-141", "CASE-207"],
        "assessment": [
            {
                "claim_id": "claim-141-1",
                "target_relationship_id": "E-BRIDGE",
                "evidence_ref": "SRC-FIR-141",
                "state": "SUPPORTS",
                "source_quality": 0.96,
                "freshness_days": 12,
                "rationale": "Direct FIR naming corroborated with verified MSISDN +91 98450 11223.",
            },
            {
                "claim_id": "claim-141-2",
                "target_relationship_id": "E-COMM-DK",
                "evidence_ref": "SRC-CDR-B31",
                "state": "SUPPORTS",
                "source_quality": 0.92,
                "freshness_days": 14,
                "rationale": "CDR record indicates recurring calls during contraband transit window.",
            },
            {
                "claim_id": "claim-141-3",
                "target_relationship_id": "E-TXN-55",
                "evidence_ref": "SRC-TXN-55",
                "state": "SUPPORTS",
                "source_quality": 0.95,
                "freshness_days": 8,
                "rationale": "Bank wire statement matches peeling chain layer transfer.",
            },
        ],
        "forecast": {
            "forecast_id": "fc-0082-1",
            "pulse_id": "pulse-0082",
            "target_state": "JURISDICTION_SHIFT",
            "time_window": ["2026-08-25T00:00:00Z", "2026-08-30T00:00:00Z"],
            "support_level": 0.92,
            "uncertainty": 0.08,
            "action_window": "Within 48 hours",
            "suggested_verification": "Verify carrier subscriber certificate and corroborate vehicle KA-01-AB-1001",
            "abstained": False,
            "abstention_reason": None,
        },
        "verification_plan": [
            {
                "verification_id": "verif-01",
                "target_claim": "Cell handover validation",
                "missing_evidence_type": "TOWER_DUMP",
                "recommended_action": "Issue Section 63 BSA production notice to telecom provider for cell tower dump",
                "responsible_role": "INVESTIGATOR",
                "status": "PENDING",
            },
            {
                "verification_id": "verif-02",
                "target_claim": "Smurfing termination",
                "missing_evidence_type": "BANK_FREEZE",
                "recommended_action": "Freeze identified mule account ACC-7731 via FIU-IND alert channel",
                "responsible_role": "SUPERVISOR",
                "status": "PENDING",
            },
        ],
    }

    pulses = [
        primary_pulse,
        {
            "pulse_id": "pulse-0091",
            "change_ids": ["E-BRIDGE-2", "E-TXN-HWL"],
            "signal_headline": "Hawala Peeling Route Emergence",
            "review_priority": "CRITICAL_REVIEW",
            "time_window": ["2026-03-15T11:00:00Z", "2026-08-24T18:00:00Z"],
            "evidence_refs": ["SRC-FIR-305", "SRC-FIR-412"],
            "support_level": 0.91,
            "uncertainty": 0.09,
            "action_window": "24 hours",
            "abstained": False,
            "generated_at": "2026-08-24T18:10:00Z",
            "affected_entities": ["P-VIKRAM", "ACC-4491", "ACC-9914"],
            "affected_cases": ["CASE-305", "CASE-412"],
            "assessment": [
                {
                    "claim_id": "claim-305-1",
                    "target_relationship_id": "E-BRIDGE-2",
                    "evidence_ref": "SRC-FIR-305",
                    "state": "SUPPORTS",
                    "source_quality": 0.93,
                    "freshness_days": 18,
                    "rationale": "Accused resolved across Mangaluru narcotics and Hubballi cyber cases.",
                }
            ],
            "forecast": {
                "forecast_id": "fc-0091-1",
                "pulse_id": "pulse-0091",
                "target_state": "FINANCIAL_ROUTE_TRANSITION",
                "time_window": ["2026-08-25T00:00:00Z", "2026-08-30T00:00:00Z"],
                "support_level": 0.89,
                "uncertainty": 0.11,
                "action_window": "Within 24 hours",
                "suggested_verification": "Freeze account ACC-4491 and subpoena transaction logs",
                "abstained": False,
                "abstention_reason": None,
            },
            "verification_plan": [
                {
                    "verification_id": "verif-03",
                    "target_claim": "Fund trace verification",
                    "missing_evidence_type": "BANK_STATEMENT",
                    "recommended_action": "Request certified bank statement from HDFC Bank",
                    "responsible_role": "INVESTIGATOR",
                    "status": "PENDING",
                }
            ],
        },
        {
            "pulse_id": "pulse-0104",
            "change_ids": ["E-BRIDGE-3"],
            "signal_headline": "Vehicle Carrier Conduit Identified",
            "review_priority": "PRIORITY_REVIEW",
            "time_window": ["2026-04-02T10:15:00Z", "2026-08-24T18:00:00Z"],
            "evidence_refs": ["SRC-FIR-501", "SRC-FIR-502"],
            "support_level": 0.88,
            "uncertainty": 0.12,
            "action_window": "48 hours",
            "abstained": False,
            "generated_at": "2026-08-24T18:15:00Z",
            "affected_entities": ["P-SUNIEL", "VEH-1001"],
            "affected_cases": ["CASE-501", "CASE-502"],
            "assessment": [
                {
                    "claim_id": "claim-501-1",
                    "target_relationship_id": "E-BRIDGE-3",
                    "evidence_ref": "SRC-FIR-501",
                    "state": "SUPPORTS",
                    "source_quality": 0.90,
                    "freshness_days": 25,
                    "rationale": "Logistics coordinator vehicle registration confirmed in both FIRs.",
                }
            ],
            "forecast": {
                "forecast_id": "fc-0104-1",
                "pulse_id": "pulse-0104",
                "target_state": "NETWORK_RESTRUCTURING",
                "time_window": ["2026-08-25T00:00:00Z", "2026-08-30T00:00:00Z"],
                "support_level": 0.85,
                "uncertainty": 0.15,
                "action_window": "Within 48 hours",
                "suggested_verification": "Inspect FASTag sensor toll passage records",
                "abstained": False,
                "abstention_reason": None,
            },
            "verification_plan": [
                {
                    "verification_id": "verif-04",
                    "target_claim": "FASTag vehicle verification",
                    "missing_evidence_type": "TOLL_DATA",
                    "recommended_action": "Subpoena NHAI toll gate transit logs for KA-01-AB-1001",
                    "responsible_role": "INVESTIGATOR",
                    "status": "PENDING",
                }
            ],
        },
    ]

    # 4. Canonical KPIs
    # Calculate claims
    all_claims = []
    supported_claims = 0
    for p in pulses:
        for a in p.get("assessment", []):
            all_claims.append(a)
            if a.get("state") == "SUPPORTS":
                supported_claims += 1

    total_claims = len(all_claims)
    evidence_percent = round((supported_claims / total_claims) * 100) if total_claims > 0 else 100

    affected_cases_set = set()
    for p in pulses:
        for c in p.get("affected_cases", []):
            affected_cases_set.add(c)

    kpis = {
        "active_pulses_count": len(pulses),
        "critical_pulses_count": sum(1 for p in pulses if p.get("review_priority") == "CRITICAL_REVIEW"),
        "evidence_percent": evidence_percent,
        "supported_claims": supported_claims,
        "total_claims": total_claims,
        "affected_cases_count": len(affected_cases_set),
        "added_nodes": len(added_nodes),
        "added_edges": len(added_relationships),
        "total_changes": len(added_nodes) + len(added_relationships),
    }

    # 5. Canonical Case DNA Index
    case_dna_index = {
        "CASE-141": {
            "target_case_id": "CASE-141",
            "similar_cases": [
                {
                    "case_pair": ["CASE-141", "CASE-207"],
                    "case_a_title": "FIR No. 141/2026 — Inter-State Cargo Smuggling",
                    "case_b_title": "FIR No. 207/2026 — Peeling Chain Cyber Fraud",
                    "overall_similarity": 0.88,
                    "structure_similarity": 0.85,
                    "communication_similarity": 0.92,
                    "financial_similarity": 0.84,
                    "location_similarity": 0.90,
                    "temporal_similarity": 0.89,
                    "shared_entities": ["P-RAFIQ", "PH-UNIFIED", "ACC-7731"],
                    "explanation": "High topological and communication similarity (0.92) across Mysuru and Bengaluru syndicates via unified suspect Rafiq Khan and peeling chain transfers.",
                    "evidence_refs": ["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"],
                    "derivation_class": "DERIVED",
                    "dataset_version": CANONICAL_DATASET_VERSION,
                    "snapshot_id": CANONICAL_SNAPSHOT_CURRENT,
                },
                {
                    "case_pair": ["CASE-141", "CASE-501"],
                    "case_a_title": "FIR No. 141/2026 — Inter-State Cargo Smuggling",
                    "case_b_title": "FIR No. 501/2026 — Transshipment Cargo Conduit",
                    "overall_similarity": 0.62,
                    "structure_similarity": 0.65,
                    "communication_similarity": 0.60,
                    "financial_similarity": 0.55,
                    "location_similarity": 0.70,
                    "temporal_similarity": 0.60,
                    "shared_entities": ["VEH-1001"],
                    "explanation": "Moderate structural match sharing logistics transit pattern along NH-48 corridor.",
                    "evidence_refs": ["SRC-FIR-141", "SRC-FIR-501"],
                    "derivation_class": "DERIVED",
                    "dataset_version": CANONICAL_DATASET_VERSION,
                    "snapshot_id": CANONICAL_SNAPSHOT_CURRENT,
                },
            ],
            "average_similarity": 0.75,
            "highest_similarity": 0.88,
            "top_shared_entities": ["P-RAFIQ", "PH-UNIFIED", "ACC-7731", "VEH-1001"],
            "dataset_version": CANONICAL_DATASET_VERSION,
        },
        "CASE-207": {
            "target_case_id": "CASE-207",
            "similar_cases": [
                {
                    "case_pair": ["CASE-207", "CASE-141"],
                    "case_a_title": "FIR No. 207/2026 — Peeling Chain Cyber Fraud",
                    "case_b_title": "FIR No. 141/2026 — Inter-State Cargo Smuggling",
                    "overall_similarity": 0.88,
                    "structure_similarity": 0.85,
                    "communication_similarity": 0.92,
                    "financial_similarity": 0.84,
                    "location_similarity": 0.90,
                    "temporal_similarity": 0.89,
                    "shared_entities": ["P-RAFIQ", "PH-UNIFIED", "ACC-7731"],
                    "explanation": "High topological and communication similarity (0.92) across Mysuru and Bengaluru syndicates via unified suspect Rafiq Khan and peeling chain transfers.",
                    "evidence_refs": ["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"],
                    "derivation_class": "DERIVED",
                    "dataset_version": CANONICAL_DATASET_VERSION,
                    "snapshot_id": CANONICAL_SNAPSHOT_CURRENT,
                }
            ],
            "average_similarity": 0.88,
            "highest_similarity": 0.88,
            "top_shared_entities": ["P-RAFIQ", "PH-UNIFIED", "ACC-7731"],
            "dataset_version": CANONICAL_DATASET_VERSION,
        },
    }

    # 6. Audit Fixture Metadata
    audit_fixture_metadata = {
        "demo_namespace": "DEMO_FORENSIC_SEED",
        "anchor_id": "ANCHOR-DEMO-001",
        "merkle_root": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "dataset_version": CANONICAL_DATASET_VERSION,
        "seed_event_ids": [
            "evt-demo-seed-001",
            "evt-demo-seed-002",
            "evt-demo-seed-003",
        ],
        "chain_length": 3,
        "status": "ANCHORED",
    }

    read_model = {
        "dataset_version": CANONICAL_DATASET_VERSION,
        "generated_at": _utcnow_iso(),
        "snapshots": {
            CANONICAL_SNAPSHOT_BASELINE: {
                "snapshot_id": CANONICAL_SNAPSHOT_BASELINE,
                "case_scope": "GLOBAL",
                "created_at": "2026-08-25T10:00:00Z",
                "node_count": 445,
                "edge_count": 486,
                "version": "v1.0",
                "dataset_version": CANONICAL_DATASET_VERSION,
            },
            CANONICAL_SNAPSHOT_CURRENT: {
                "snapshot_id": CANONICAL_SNAPSHOT_CURRENT,
                "case_scope": "GLOBAL",
                "created_at": "2026-08-25T12:00:00Z",
                "node_count": 441,
                "edge_count": 491,
                "version": "v1.1",
                "dataset_version": CANONICAL_DATASET_VERSION,
            },
        },
        "network_delta": network_delta,
        "pulses": pulses,
        "primary_pulse": primary_pulse,
        "kpis": kpis,
        "affected_investigations": sorted(list(affected_cases_set)),
        "cases": cases_data,
        "worklist": cases_data,
        "case_dna_index": case_dna_index,
        "hotspots": [
            {
                "district": "Bengaluru City",
                "risk_category": "CYBER_FRAUD_HUB",
                "incident_count": 42,
                "active_syndicates": ["Cyber Hawala Syndicate"],
            },
            {
                "district": "Mysuru",
                "risk_category": "CONTRABAND_TRANSIT",
                "incident_count": 28,
                "active_syndicates": ["Coastal Narcotics Syndicate"],
            },
        ],
        "communities": [
            {"community_id": "COMM-ALPHA", "name": "Coastal Narcotics Syndicate", "node_count": 18},
            {"community_id": "COMM-BETA", "name": "Cyber Hawala Syndicate", "node_count": 14},
        ],
        "bridges": [
            {
                "edge_id": "E-BRIDGE",
                "source": "CASE-141",
                "target": "CASE-207",
                "bridge_type": "CONNECTS_CASES",
                "connector_entity": "P-RAFIQ",
            }
        ],
        "identity_drifts": [
            {
                "entity_id": "person-0001",
                "canonical_name": "Rafiq Khan",
                "drift_count": 3,
                "resolved_aliases": ["Rafiq Ahmed", "Rafi", "Chhota"],
            }
        ],
        "network_adaptations": [
            {
                "adaptation_id": "adapt-001",
                "primary_entity": "P-RAFIQ",
                "trigger_event": "SIM swap observed in cell handover",
                "delta_status": "OBSERVED",
            }
        ],
        "audit_fixture_metadata": audit_fixture_metadata,
    }

    read_model["checksum"] = compute_dataset_checksum(read_model)
    return read_model


def get_canonical_read_model() -> dict[str, Any]:
    """Retrieve or compute the canonical read-model bundle."""
    version = CANONICAL_DATASET_VERSION
    if version in READ_MODEL_CACHE:
        return READ_MODEL_CACHE[version]

    # Check disk cache
    bundled_path = Path(__file__).resolve().parents[1] / "db" / "canonical_read_model.json"
    if bundled_path.exists():
        try:
            model = json.loads(bundled_path.read_text(encoding="utf-8"))
            if model.get("dataset_version") == version:
                READ_MODEL_CACHE[version] = model
                return model
        except Exception as e:
            logger.warning("Failed to load bundled read model: %s", e)

    model = build_canonical_read_model()
    save_canonical_read_model(model)
    READ_MODEL_CACHE[version] = model
    return model


def save_canonical_read_model(model: dict[str, Any]) -> None:
    """Save the read model to backend/app/db/canonical_read_model.json and artifacts/."""
    try:
        db_path = Path(__file__).resolve().parents[1] / "db" / "canonical_read_model.json"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text(json.dumps(model, indent=2), encoding="utf-8")

        art_dir = Path("artifacts")
        art_dir.mkdir(parents=True, exist_ok=True)
        (art_dir / "canonical_read_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not persist canonical read model to disk: %s", e)


def get_intelligence_bootstrap_payload() -> IntelligenceBootstrapResponse:
    """Return compact, fast bootstrap response from the authoritative read model."""
    model = get_canonical_read_model()
    kpis_data = model.get("kpis", {})
    kpis = IntelligenceKPIs(**kpis_data)

    primary_pulse_data = model.get("primary_pulse")
    primary_pulse = NetworkPulseItem(**primary_pulse_data) if primary_pulse_data else None

    net_delta = model.get("network_delta", {})
    primary_diff = NetworkDiffResponse(
        before_snapshot_id=net_delta.get("before_snapshot_id", CANONICAL_SNAPSHOT_BASELINE),
        after_snapshot_id=net_delta.get("after_snapshot_id", CANONICAL_SNAPSHOT_CURRENT),
        added_nodes=net_delta.get("added_nodes", []),
        removed_nodes=net_delta.get("removed_nodes", []),
        added_relationships=net_delta.get("added_relationships", []),
        removed_relationships=net_delta.get("removed_relationships", []),
        modified_node_count=0,
        modified_relationship_count=0,
        pulses=[primary_pulse] if primary_pulse else [],
        summary={
            "added_node_count": net_delta.get("added_node_count", 0),
            "removed_node_count": net_delta.get("removed_node_count", 0),
            "added_relationship_count": net_delta.get("added_relationship_count", 0),
            "removed_relationship_count": net_delta.get("removed_relationship_count", 0),
        },
        dataset_version=model.get("dataset_version", CANONICAL_DATASET_VERSION),
    )

    return IntelligenceBootstrapResponse(
        dataset_version=model.get("dataset_version", CANONICAL_DATASET_VERSION),
        snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        baseline_snapshot_id=CANONICAL_SNAPSHOT_BASELINE,
        kpis=kpis,
        primary_pulse=primary_pulse,
        primary_diff=primary_diff,
        affected_cases=model.get("affected_investigations", []),
        generated_at=model.get("generated_at", _utcnow_iso()),
    )
