"""tests/test_canonical_read_model.py

Targeted verification for Phase 2: Canonical demo/read-model pipeline.
Ensures the read model is generated deterministically, contains checksums,
resolves evidence references, and reflects the canonical graph and Case DNA pairs.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.canonical_read_model import (
    build_canonical_read_model,
    get_canonical_read_model,
    get_intelligence_bootstrap_payload,
)
from shared.contracts.api import (
    CANONICAL_DATASET_VERSION,
    CANONICAL_SNAPSHOT_BASELINE,
    CANONICAL_SNAPSHOT_CURRENT,
)


def test_canonical_read_model_structure() -> None:
    """Verify read model contains all required canonical sections and checksum."""
    model = get_canonical_read_model()
    assert model["dataset_version"] == CANONICAL_DATASET_VERSION
    assert "checksum" in model and model["checksum"].startswith("sha256:")
    assert "generated_at" in model

    # Check snapshots
    snapshots = model.get("snapshots", {})
    assert CANONICAL_SNAPSHOT_BASELINE in snapshots
    assert CANONICAL_SNAPSHOT_CURRENT in snapshots
    assert snapshots[CANONICAL_SNAPSHOT_BASELINE]["snapshot_id"] == "snap-baseline-v1"
    assert snapshots[CANONICAL_SNAPSHOT_CURRENT]["snapshot_id"] == "snap-current"


def test_canonical_cases_and_worklist() -> None:
    """Verify expected cases exist in cases and worklist."""
    model = get_canonical_read_model()
    cases = model.get("cases", [])
    case_ids = {c["case_id"] for c in cases}
    assert "CASE-141" in case_ids
    assert "CASE-207" in case_ids
    assert "CASE-305" in case_ids
    assert "CASE-412" in case_ids
    assert "CASE-501" in case_ids
    assert "CASE-502" in case_ids

    # Verify worklist mirrors cases with attention queue attributes
    worklist = model.get("worklist", [])
    for row in worklist:
        assert "status" in row
        assert "priority" in row
        assert "last_activity" in row
        assert "evidence_state" in row
        assert "jurisdictions" in row
        assert "next_action" in row


def test_network_delta_and_bridge_changes() -> None:
    """Verify E-BRIDGE and change data exist in network delta."""
    model = get_canonical_read_model()
    delta = model.get("network_delta", {})
    assert "E-BRIDGE" in delta.get("added_relationships", [])
    assert "P-RAFIQ" in delta.get("added_nodes", [])
    assert delta.get("added_relationship_count", 0) >= 6
    assert delta.get("added_node_count", 0) >= 4


def test_case_dna_demo_relationship() -> None:
    """Verify Case DNA demo relationship between CASE-141 and CASE-207 exists."""
    model = get_canonical_read_model()
    dna_index = model.get("case_dna_index", {})
    assert "CASE-141" in dna_index
    case_141_matches = dna_index["CASE-141"]["similar_cases"]
    pair_ids = [m["case_pair"] for m in case_141_matches]
    assert any(p == ["CASE-141", "CASE-207"] for p in pair_ids)

    match_207 = next(m for m in case_141_matches if m["case_pair"] == ["CASE-141", "CASE-207"])
    assert match_207["overall_similarity"] >= 0.85
    assert "P-RAFIQ" in match_207["shared_entities"]
    assert match_207["dataset_version"] == CANONICAL_DATASET_VERSION


def test_evidence_references_resolution() -> None:
    """Verify evidence references in pulses match canonical source records."""
    model = get_canonical_read_model()
    pulses = model.get("pulses", [])
    assert len(pulses) >= 3

    all_evidence_refs = set()
    for p in pulses:
        all_evidence_refs.update(p.get("evidence_refs", []))
        for a in p.get("assessment", []):
            if a.get("evidence_ref"):
                all_evidence_refs.add(a["evidence_ref"])

    # Ensure canonical forensic citations are present
    expected_sources = {"SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"}
    assert expected_sources.issubset(all_evidence_refs)


def test_intelligence_bootstrap_generation() -> None:
    """Verify fast bootstrap response helper produces valid payload."""
    bootstrap = get_intelligence_bootstrap_payload()
    assert bootstrap.dataset_version == CANONICAL_DATASET_VERSION
    assert bootstrap.snapshot_id == CANONICAL_SNAPSHOT_CURRENT
    assert bootstrap.baseline_snapshot_id == CANONICAL_SNAPSHOT_BASELINE
    assert bootstrap.kpis.active_pulses_count >= 3
    assert bootstrap.kpis.total_changes >= 10
    assert bootstrap.primary_pulse is not None
    assert bootstrap.primary_pulse.pulse_id == "pulse-0082"
    assert "CASE-141" in bootstrap.affected_cases
    assert "CASE-207" in bootstrap.affected_cases
