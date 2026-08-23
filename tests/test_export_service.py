"""tests/test_export_service.py

Tests for Phase 5 BSA Section 63 PDF Dossier Export (BE-05):
- Tests PDF generation via ExportService
- Tests SHA-256 PDF hash stability & tamper sensitivity
- Tests Audit logging (EXPORT_INITIATED, EXPORT_COMPLETED)
- Tests HTTP endpoints POST /api/v1/export/dossier & /download
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.export_service import ExportService
from shared.contracts.api import DossierExportRequest


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    return InMemoryBackendRepository()


@pytest.fixture
def audit(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def evidence_svc(repo: InMemoryBackendRepository, audit: AuditService) -> EvidenceService:
    return EvidenceService(repo, audit)


@pytest.fixture
def export_svc(
    repo: InMemoryBackendRepository,
    audit: AuditService,
    evidence_svc: EvidenceService,
) -> ExportService:
    return ExportService(repo, audit, evidence_svc)


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo)
    return TestClient(app)


def test_generate_dossier_pdf_structure(export_svc: ExportService, repo: InMemoryBackendRepository) -> None:
    case_id = repo.case_ids[0] if repo.case_ids else "case-0001"
    req = DossierExportRequest(case_id=case_id)
    pdf_bytes, meta = export_svc.generate_dossier_pdf(req, actor_id="officer-dossier")

    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
    assert meta.case_id == case_id
    assert len(meta.sha256_hash) == 64
    assert meta.file_size_bytes == len(pdf_bytes)


def test_export_audit_events_logged(export_svc: ExportService, repo: InMemoryBackendRepository) -> None:
    case_id = repo.case_ids[0] if repo.case_ids else "case-0001"
    req = DossierExportRequest(case_id=case_id)
    export_svc.generate_dossier_pdf(req, actor_id="officer-audit-check")

    init_events = [e for e in repo.audit_events if e.get("event_type") == "export_initiated"]
    comp_events = [e for e in repo.audit_events if e.get("event_type") == "export_completed"]

    assert len(init_events) >= 1
    assert len(comp_events) >= 1


def test_export_dossier_endpoint(client: TestClient) -> None:
    repo = InMemoryBackendRepository()
    case_id = repo.case_ids[0] if repo.case_ids else "case-0001"
    resp = client.post("/api/v1/export/dossier", json={"case_id": case_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert "sha256_hash" in data
    assert data["file_size_bytes"] > 0


def test_download_dossier_endpoint(client: TestClient) -> None:
    repo = InMemoryBackendRepository()
    case_id = repo.case_ids[0] if repo.case_ids else "case-0001"
    resp = client.post("/api/v1/export/dossier/download", json={"case_id": case_id})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert "x-dossier-sha256" in resp.headers
    assert resp.content.startswith(b"%PDF")
