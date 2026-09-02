"""tests/test_blockchain_audit_anchoring.py

Comprehensive tests for NEXUS Trust Layer - Phase 4:
Permissioned Blockchain Audit Anchoring.

Covers:
  1. RFC 6962 deterministic binary Merkle tree root calculation.
  2. Sequential block indices and previous_block_hash cryptographic linkage.
  3. AuditAnchorService: Anchoring audit event batches to permissioned blocks.
  4. Non-recursive audit logging: Anchoring does not cause infinite self-anchoring loops.
  5. Anchor verification: Successful verification when untouched.
  6. Tamper demonstration (MANDATORY TEST):
     - Mutating audit event fails audit verification.
     - Mutating anchored root or block hash fails blockchain verification (fail closed).
     - Breaking ledger block chain fails ledger chain validation.
  7. Multi-node permissioned participant attribution (HQ, Cyber Cell, District).
  8. Endpoints:
     - POST /api/v1/audit/anchors
     - GET /api/v1/audit/anchors
     - GET /api/v1/audit/anchors/{anchor_id}
     - GET /api/v1/audit/anchors/{anchor_id}/verify
     - RBAC permission checks (anonymous denied 403, authorized officer 200).
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.core.blockchain.ledger import (
    LedgerParticipant,
    PermissionedLedger,
)
from backend.app.core.crypto.audit_integrity import verify_audit_event_integrity
from backend.app.core.crypto.merkle import compute_merkle_root
from backend.app.main import create_app
from backend.app.services.audit_anchor_service import AuditAnchorService
from backend.app.services.audit_service import AuditEventType, AuditService


def _make_demo_token(user_id: str, role: str) -> str:
    """Helper to generate a valid base64 demo token matching frontend AuthContext session."""
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


# 1. Merkle Tree calculation tests
def test_merkle_tree_deterministic_root() -> None:
    h1 = "a" * 64
    h2 = "b" * 64
    h3 = "c" * 64

    root1 = compute_merkle_root([h1, h2, h3])
    root2 = compute_merkle_root([h1, h2, h3])
    assert len(root1) == 64
    assert root1 == root2

    # Different inputs produce different roots
    root3 = compute_merkle_root([h1, h2, "d" * 64])
    assert root1 != root3


# 2. Permissioned ledger chain formation
def test_permissioned_ledger_genesis_and_blocks() -> None:
    ledger = PermissionedLedger()
    assert len(ledger.chain) == 1
    assert ledger.chain[0].index == 0
    assert ledger.chain[0].previous_hash == "0" * 64
    assert ledger.chain[0].block_hash != ""

    # Append first anchor
    anchor = ledger.append_anchor(
        anchor_id="ANCHOR-1",
        batch_start="evt-1",
        batch_end="evt-2",
        event_hashes=["1" * 64, "2" * 64],
        participant=LedgerParticipant.CYBER_CELL,
    )
    assert len(ledger.chain) == 2
    assert ledger.chain[1].index == 1
    assert ledger.chain[1].previous_hash == ledger.chain[0].block_hash
    assert ledger.chain[1].participant == LedgerParticipant.CYBER_CELL.value
    assert anchor.root_hash == compute_merkle_root(["1" * 64, "2" * 64])

    valid, reason = ledger.verify_ledger_chain()
    assert valid is True
    assert "fully valid" in reason


# 3. AuditAnchorService batch collection & anchoring
def test_anchor_service_creates_anchor_and_verifies() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)
    ledger = PermissionedLedger()
    anchor_svc = AuditAnchorService(ledger=ledger, audit_service=audit_svc)

    # Record 3 events
    for i in range(3):
        audit_svc.record(
            event_type=AuditEventType.EVIDENCE_VIEWED,
            actor_id=f"officer_{i}",
            case_id="case-1",
            details={"seq": i},
        )

    anchor = anchor_svc.anchor_audit_batch(participant=LedgerParticipant.POLICE_HQ, actor_id="officer_sp")
    assert anchor.event_count >= 3
    assert anchor.anchor_id.startswith("ANCHOR-2026-")

    # Verify anchor
    res = anchor_svc.verify_anchor(anchor.anchor_id, actor_id="officer_sp")
    assert res.verified is True
    assert res.chain_valid is True
    assert res.block_index == 1
    assert res.root_hash == anchor.root_hash


# 4. Non-recursive audit logging
def test_anchor_service_non_recursive() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)
    ledger = PermissionedLedger()
    anchor_svc = AuditAnchorService(ledger=ledger, audit_service=audit_svc)

    audit_svc.record(
        event_type=AuditEventType.INVESTIGATION_VIEWED,
        actor_id="officer_1",
        case_id="case-1",
    )
    events_before = len(repo.audit_events)

    # Anchor once
    anchor_svc.anchor_audit_batch(actor_id="officer_sp")
    # Anchoring creates exactly 1 audit event (AUDIT_BATCH_ANCHORED)
    assert len(repo.audit_events) == events_before + 1

    last_event = repo.audit_events[-1]
    assert last_event["event_type"] == AuditEventType.AUDIT_BATCH_ANCHORED.value


# 5. Mandatory Demo Tamper Scenario
def test_tamper_detection_both_layers() -> None:
    """Demonstrates tamper-detection at both the audit level and the blockchain level."""
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)
    ledger = PermissionedLedger()
    anchor_svc = AuditAnchorService(ledger=ledger, audit_service=audit_svc)

    # A. Create several audit events
    audit_svc.record(
        event_type=AuditEventType.LEAD_ACTIONED,
        actor_id="officer_io",
        case_id="case-0001",
        details={"decision": "CONFIRM"},
    )
    ev = repo.audit_events[-1]
    ev_hash = ev["integrity_hash"]

    # B. Anchor them to the permissioned ledger
    anchor = anchor_svc.anchor_audit_batch(actor_id="officer_sp")

    # C. Verify anchor successfully
    anchor_res = anchor_svc.verify_anchor(anchor.anchor_id)
    assert anchor_res.verified is True

    # D. Verify blockchain chain successfully
    chain_ok, _ = ledger.verify_ledger_chain()
    assert chain_ok is True

    # E. Mutate audit event
    tampered_ev = dict(ev)
    tampered_ev["details"] = {"decision": "REJECT"}

    # F. Confirm audit SHA-256 verification fails
    assert verify_audit_event_integrity(tampered_ev).verified is False

    # G. Mutate the blockchain block/anchor data
    # (Simulating adversary attempting to rewrite anchored Merkle root in the ledger block)
    block = ledger.chain[1]
    original_block_hash = block.block_hash
    tampered_anchor = block.anchors[0]
    # Replace anchor in block with altered root hash without re-signing or updating block hash
    block.anchors = [
        type(tampered_anchor)(
            anchor_id=tampered_anchor.anchor_id,
            batch_start=tampered_anchor.batch_start,
            batch_end=tampered_anchor.batch_end,
            event_count=tampered_anchor.event_count,
            root_hash="f" * 64,  # altered root
            anchored_at=tampered_anchor.anchored_at,
            creator_participant=tampered_anchor.creator_participant,
            ledger_id=tampered_anchor.ledger_id,
            event_hashes=tampered_anchor.event_hashes,
        )
    ]

    # H. Confirm blockchain verification fails (fail closed)
    fail_res = ledger.verify_anchor(anchor.anchor_id)
    assert fail_res.verified is False
    assert "Ledger integrity failure" in fail_res.reason or "altered" in fail_res.reason or "mismatch" in fail_res.reason

    chain_valid, chain_reason = ledger.verify_ledger_chain()
    assert chain_valid is False
    assert "hash altered" in chain_reason.lower()


# 6. API Endpoints
def test_blockchain_anchor_api_endpoints() -> None:
    app = create_app()
    client = TestClient(app)

    # 1. Seed an audit event
    sp_token = _make_demo_token("officer_sp", "SP")
    client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "CONFIRM", "decided_by": "Investigating Officer"},
        headers={"Authorization": f"Bearer {sp_token}"},
    )

    # 2. POST /api/v1/audit/anchors
    create_resp = client.post(
        "/api/v1/audit/anchors",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert create_resp.status_code == 200
    anc = create_resp.json()
    assert "anchor_id" in anc
    anchor_id = anc["anchor_id"]

    # 3. GET /api/v1/audit/anchors
    list_resp = client.get(
        "/api/v1/audit/anchors",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert list_resp.status_code == 200
    anchors_list = list_resp.json()
    assert any(a["anchor_id"] == anchor_id for a in anchors_list)

    # 4. GET /api/v1/audit/anchors/{anchor_id}
    detail_resp = client.get(
        f"/api/v1/audit/anchors/{anchor_id}",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["anchor_id"] == anchor_id

    # 5. GET /api/v1/audit/anchors/{anchor_id}/verify
    verify_resp = client.get(
        f"/api/v1/audit/anchors/{anchor_id}/verify",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verified"] is True
    assert verify_data["chain_valid"] is True

    # 6. Unauthorized access check (anonymous caller denied 403)
    anon_resp = client.post("/api/v1/audit/anchors")
    assert anon_resp.status_code == 403

    anon_verify = client.get(f"/api/v1/audit/anchors/{anchor_id}/verify")
    assert anon_verify.status_code == 403
