"""tests/test_audit_idempotent_bootstrap.py

Verifies Phase 13 requirements:
- Explicit, idempotent demo bootstrap
- Deterministic event IDs and anchor ID
- Idempotency: repeated executions create no duplicate events or anchors
- Explicit proof states: VERIFIED, NOT_YET_ANCHORED, UNKNOWN_EVENT
"""

from __future__ import annotations

import pytest

from backend.app.core.blockchain.ledger import PermissionedLedger
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_anchor_service import (
    AuditAnchorService,
)
from backend.app.services.audit_service import AuditEventType, AuditService


@pytest.fixture
def audit_setup():
    repo = InMemoryBackendRepository()
    audit_svc = AuditService(repo)
    ledger = PermissionedLedger()
    anchor_svc = AuditAnchorService(ledger=ledger, audit_service=audit_svc)
    return anchor_svc, audit_svc, ledger


def test_audit_demo_bootstrap_idempotency(audit_setup) -> None:
    anchor_svc, audit_svc, ledger = audit_setup

    # First bootstrap
    anchor_id_1 = anchor_svc.bootstrap_demo_audit()
    assert anchor_id_1 == "ANCHOR-2026-DEMO-001"
    initial_event_count = len(audit_svc.list_events(limit=100))
    initial_chain_length = len(ledger.chain)

    assert initial_event_count >= 5
    assert initial_chain_length == 2  # Genesis block + 1 demo anchor block

    # Second bootstrap (must be completely idempotent)
    anchor_id_2 = anchor_svc.bootstrap_demo_audit()
    assert anchor_id_2 == "ANCHOR-2026-DEMO-001"
    assert len(audit_svc.list_events(limit=100)) == initial_event_count
    assert len(ledger.chain) == initial_chain_length

    # Third bootstrap with force=False
    anchor_id_3 = anchor_svc.bootstrap_demo_audit(force=False)
    assert anchor_id_3 == "ANCHOR-2026-DEMO-001"
    assert len(audit_svc.list_events(limit=100)) == initial_event_count
    assert len(ledger.chain) == initial_chain_length


def test_audit_proof_states(audit_setup) -> None:
    anchor_svc, audit_svc, ledger = audit_setup

    # Bootstrap demo events and anchor
    anchor_svc.bootstrap_demo_audit()

    # 1. VERIFIED state: seeded and anchored event
    proof_1 = anchor_svc.get_event_proof_status("EVT-DEMO-001")
    assert proof_1["status"] == "VERIFIED"
    assert proof_1["verified"] is True
    assert proof_1["anchor_id"] == "ANCHOR-2026-DEMO-001"
    assert len(proof_1["proof"]) > 0

    # 2. UNKNOWN_EVENT state: event does not exist in repository
    proof_unknown = anchor_svc.get_event_proof_status("NON-EXISTENT-EVENT-999")
    assert proof_unknown["status"] == "UNKNOWN_EVENT"
    assert proof_unknown["verified"] is False

    # 3. NOT_YET_ANCHORED state: record new unanchored event
    new_evt_id = "EVT-FRESH-001"
    audit_svc.record(
        event_type=AuditEventType.INVESTIGATION_VIEWED,
        actor_id="officer-fresh",
        case_id="CASE-141",
        event_id=new_evt_id,
    )
    proof_unanchored = anchor_svc.get_event_proof_status(new_evt_id)
    assert proof_unanchored["status"] == "NOT_YET_ANCHORED"
    assert proof_unanchored["verified"] is False
