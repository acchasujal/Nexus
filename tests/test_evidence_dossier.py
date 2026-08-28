from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditService
from backend.app.services.evidence_dossier_service import EvidenceDossierService
from backend.app.services.evidence_service import EvidenceService
from shared.contracts.api import NexusDossierRequest
from types import SimpleNamespace


@pytest.fixture
def dossier_context() -> tuple[InMemoryBackendRepository, EvidenceDossierService, str, str]:
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    evidence = EvidenceService(repo, audit)
    service = EvidenceDossierService(repo, audit, evidence_service=evidence)
    case_id = repo.case_ids[0]
    evidence_id = evidence.list_all_evidence(case_id=case_id, actor_id="test")[0].id
    return repo, service, case_id, evidence_id


def test_case_dossier_contains_authoritative_evidence_and_pdf_hash(dossier_context) -> None:
    _, service, case_id, evidence_id = dossier_context
    pdf, metadata = service.generate_dossier(NexusDossierRequest(case_id=case_id), actor_id="investigator")

    assert pdf.startswith(b"%PDF")
    assert metadata.case_id == case_id
    assert evidence_id in metadata.evidence_ids
    assert metadata.pdf_sha256 == hashlib.sha256(pdf).hexdigest()
    assert metadata.evidence_hashes[evidence_id]


def test_dossier_verification_detects_tampered_pdf(dossier_context) -> None:
    _, service, case_id, _ = dossier_context
    _, metadata = service.generate_dossier(NexusDossierRequest(case_id=case_id))
    pdf, stored = service.get_dossier_pdf(metadata.dossier_id)
    service._dossier_cache[metadata.dossier_id] = (pdf + b"tampered", stored)

    result = service.verify_dossier_integrity(metadata.dossier_id)
    assert result["verified"] is False
    assert result["expected_hash"] != result["computed_hash"]


def test_lead_dossier_uses_only_cited_authoritative_evidence(dossier_context) -> None:
    _, service, case_id, evidence_id = dossier_context
    service._lead_svc = SimpleNamespace(get_leads=lambda: [SimpleNamespace(
        id="LEAD-TEST",
        title="Authoritative bridge lead",
        rule_id="TEST_RULE",
        explanation="AI-assisted summary grounded in the cited record.",
        review_priority="HIGH",
        case_ids=[case_id],
        entity_ids=[],
        evidence_ids=[evidence_id],
        path=None,
    )])

    pdf, metadata = service.generate_dossier(NexusDossierRequest(lead_id="LEAD-TEST"))
    assert pdf.startswith(b"%PDF")
    assert metadata.lead_id == "LEAD-TEST"
    assert metadata.evidence_ids == [evidence_id]


def test_missing_case_and_evidence_fail_closed(dossier_context) -> None:
    _, service, _, _ = dossier_context
    with pytest.raises(KeyError, match="not found"):
        service.generate_dossier(NexusDossierRequest(case_id="CASE-DOES-NOT-EXIST"))
    with pytest.raises(KeyError, match="not found"):
        service.generate_dossier(NexusDossierRequest(evidence_ids=["EV-9999"]))


def test_dossier_routes_require_auth_and_verify_evidence(dossier_context) -> None:
    repo, _, case_id, evidence_id = dossier_context
    client = TestClient(create_app(repository=repo))
    generated = client.post("/api/v1/nexus/evidence/dossier", json={"case_id": case_id})
    assert generated.status_code == 200
    metadata = generated.json()

    downloaded = client.get(metadata["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF")

    verified = client.post(
        "/api/v1/nexus/evidence/verify",
        json={"evidence_ids": [evidence_id], "dossier_id": metadata["dossier_id"]},
    )
    assert verified.status_code == 200
    assert verified.json()["overall_verified"] is True

    missing = client.post("/api/v1/nexus/evidence/dossier", json={"case_id": "CASE-9999"})
    assert missing.status_code == 404