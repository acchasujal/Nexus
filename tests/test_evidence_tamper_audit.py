"""tests/test_evidence_tamper_audit.py

End-to-end test suite for Section 5: Evidence Integrity and Tampering Verification:
  1. Valid canonical evidence SHA-256 verifies successfully -> 200 OK with verified=True.
  2. Mutating the raw evidence content / excerpt causes verification failure -> verified=False with failure reason.
  3. Tampering test creates AuditEventType.EVIDENCE_INTEGRITY_MISMATCH in the immutable audit log.
  4. Non-tampered check creates AuditEventType.EVIDENCE_INTEGRITY_VERIFIED in the audit log.
"""

from __future__ import annotations

import hashlib
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType


@pytest.fixture
def repo_with_sample_evidence():
    repo = InMemoryBackendRepository()
    # Add a known canonical source record
    raw_excerpt = "FIR-2026-608: Accused Rafiq Ansari transferred 50,000 INR to Deepak Verma."
    content_hash = hashlib.sha256(raw_excerpt.encode("utf-8")).hexdigest()

    repo.source_records["SRC-EVID-TEST-001"] = {
        "id": "SRC-EVID-TEST-001",
        "source_type": "FIR",
        "locator": "FIR-2026-608:line-12",
        "raw_excerpt": raw_excerpt,
        "occurred_at": "2026-08-15T10:00:00Z",
        "batch_id": "BATCH-001",
        "case_ids": ["CASE-2026-608"],
        "content_hash": content_hash,
        "hash_algorithm": "SHA-256",
    }
    return repo


def test_evidence_verification_success(repo_with_sample_evidence):
    app = create_app(repository=repo_with_sample_evidence, settings=Settings(_env_file=None))
    with TestClient(app) as client:
        resp = client.post("/api/v1/nexus/sources/SRC-EVID-TEST-001/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_id"] == "SRC-EVID-TEST-001"
        assert data["verified"] is True
        assert data["failure_reason"] is None
        assert data["expected_hash"] == data["computed_hash"]

        # Assert audit trail entry was recorded
        last_audit = repo_with_sample_evidence.audit_events[-1]
        assert last_audit["event_type"] == AuditEventType.EVIDENCE_INTEGRITY_VERIFIED.value
        assert last_audit["entity_id"] == "SRC-EVID-TEST-001"


def test_evidence_tampering_detection(repo_with_sample_evidence):
    """MANDATORY SECURITY TEST:
    1. Verify genuine evidence H1.
    2. Tamper canonical evidence in storage.
    3. Re-verify -> Assert H1 != H2.
    4. Assert response reports verified=False and creates EVIDENCE_INTEGRITY_MISMATCH audit event.
    """
    app = create_app(repository=repo_with_sample_evidence, settings=Settings(_env_file=None))
    with TestClient(app) as client:
        # Step 1: Initial state is verified
        resp1 = client.post("/api/v1/nexus/sources/SRC-EVID-TEST-001/verify")
        assert resp1.status_code == 200
        assert resp1.json()["verified"] is True
        original_hash = resp1.json()["computed_hash"]

        # Step 2: Tamper with the raw excerpt in storage (e.g. changing amount transferred)
        tampered_excerpt = "FIR-2026-608: Accused Rafiq Ansari transferred 5,000,000 INR to Deepak Verma."
        repo_with_sample_evidence.source_records["SRC-EVID-TEST-001"]["raw_excerpt"] = tampered_excerpt

        # Step 3: Run verification again
        resp2 = client.post("/api/v1/nexus/sources/SRC-EVID-TEST-001/verify")
        assert resp2.status_code == 200
        tampered_data = resp2.json()

        # Step 4: Assert mismatch and tamper detection
        assert tampered_data["verified"] is False
        assert tampered_data["computed_hash"] != original_hash
        assert "mismatch" in tampered_data["failure_reason"].lower()

        # Step 5: Check immutable audit log
        last_audit = repo_with_sample_evidence.audit_events[-1]
        assert last_audit["event_type"] == AuditEventType.EVIDENCE_INTEGRITY_MISMATCH.value
        assert last_audit["entity_id"] == "SRC-EVID-TEST-001"
        assert last_audit["details"]["computed_hash"] != last_audit["details"]["stored_hash"]
