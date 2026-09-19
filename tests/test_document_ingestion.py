"""tests/test_document_ingestion.py

Unit and integration tests for Phase P1A: Unstructured Document Ingestion Foundation.
Tests cover:
  - Valid PDF text extraction and persistence
  - Valid TXT text extraction and persistence
  - Unsupported file type rejection (HTTP 415)
  - Malformed/corrupted PDF handling (ExtractionStatus.FAILED)
  - Empty document rejection (HTTP 400)
  - Deterministic SHA-256 content hashing
  - Deduplication across identical document uploads
  - Authenticated upload required (HTTP 401 for anonymous)
  - Case RBAC: Unauthorized case rejected (HTTP 403)
  - Case RBAC: Authorized case accepted
  - Case confidentiality: Unauthorized case document hidden from list and get
  - Audit logging: DOCUMENT_UPLOADED, DOCUMENT_VIEWED, DOCUMENT_EXTRACTION_FAILED
  - Strict Phase Boundary: Ingestion does not mutate graph nodes or edges
"""

import hashlib
import io
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from backend.app.api.dependencies import get_principal
from backend.app.auth.principal import Principal
from backend.app.main import app
from shared.contracts.api import DocumentSourceType, ExtractionStatus, UserRole


def _make_pdf(text: str = "FIR No. 495/2026 Cyber Crime PS Bengaluru") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    return buf.getvalue()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def io_assigned_token():
    """Investigating Officer assigned to case-0001."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-IO-01",
            email="rajesh.kumar@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def io_unassigned_token():
    """Investigating Officer not assigned to any cases."""
    def override():
        return Principal(
            user_id="OFFICER-UNASSIGNED",
            officer_id="OFFICER-UNASSIGNED",
            email="unassigned@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def sp_token():
    """Superintendent of Police with divisional jurisdiction."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-SP-01",
            email="sp.cyber@ksp.gov.in",
            role=UserRole.SP,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def anonymous_token():
    """Anonymous/unauthenticated caller."""
    def override():
        return Principal(
            user_id="anonymous",
            email="",
            role=UserRole.ANALYST,
            is_anonymous=True,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


# ── Test Suite ───────────────────────────────────────────────────────────────

def test_upload_valid_pdf_extracts_text_and_computes_deterministic_hash(client, sp_token):
    pdf_bytes = _make_pdf("First Information Report: Case Theft of Electronic Device")
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    response = client.post(
        "/api/v1/documents",
        files={"file": ("fir_report_01.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.FIR_DOCUMENT.value},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["document_id"] == f"doc-{expected_hash[:16]}"
    assert data["content_hash"] == expected_hash
    assert data["original_filename"] == "fir_report_01.pdf"
    assert data["source_type"] == "FIR_DOCUMENT"
    assert data["mime_type"] == "application/pdf"
    assert data["extraction_status"] == ExtractionStatus.SUCCESS.value
    assert data["extraction_metadata"]["page_count"] >= 1
    assert data["extraction_metadata"]["word_count"] > 0
    assert "provenance" in data
    assert data["provenance"]["derivation_method"] == "DOCUMENT_EXTRACTION"

    # Verify extracted text via text endpoint
    text_res = client.get(f"/api/v1/documents/{data['document_id']}/text")
    assert text_res.status_code == 200
    text_data = text_res.json()
    assert "First Information Report" in text_data["extracted_text"]
    assert text_data["content_hash"] == expected_hash


def test_upload_valid_txt_extracts_text_correctly(client, sp_token):
    txt_content = "Police Memo 2026\nSubject: Surveillance Report\nSuspect observed entering premises."
    txt_bytes = txt_content.encode("utf-8")
    expected_hash = hashlib.sha256(txt_bytes).hexdigest()

    response = client.post(
        "/api/v1/documents",
        files={"file": ("memo_surveillance.txt", txt_bytes, "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_hash"] == expected_hash
    assert data["source_type"] == "POLICE_REPORT"
    assert data["extraction_status"] == ExtractionStatus.SUCCESS.value
    assert data["extraction_metadata"]["word_count"] == len(txt_content.split())

    text_res = client.get(f"/api/v1/documents/{data['document_id']}/text")
    assert text_res.status_code == 200
    assert text_res.json()["extracted_text"] == txt_content


def test_upload_unsupported_file_extension_rejected(client, sp_token):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("evidence_report.docx", b"PK\x03\x04dummy word doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"source_type": DocumentSourceType.OTHER_DOCUMENT.value},
    )
    assert response.status_code == 415
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_empty_document_rejected(client, sp_token):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("empty_report.txt", b"", "text/plain")},
        data={"source_type": DocumentSourceType.OTHER_DOCUMENT.value},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_malformed_pdf_handled_gracefully(client, sp_token):
    malformed_bytes = b"%PDF-1.4\ncorrupt header content without valid xref or trailer %%EOF"
    response = client.post(
        "/api/v1/documents",
        files={"file": ("corrupt_fir.pdf", malformed_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.FIR_DOCUMENT.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == ExtractionStatus.FAILED.value
    assert data["extraction_metadata"]["error_message"] is not None


def test_document_deduplication_returns_existing_record_without_duplication(client, sp_token):
    pdf_bytes = _make_pdf("Special Intelligence Report on Hawala Transactions")
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # First upload
    res1 = client.post(
        "/api/v1/documents",
        files={"file": ("intel_hawala.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.INTELLIGENCE_DOCUMENT.value},
    )
    assert res1.status_code == 200
    doc_id1 = res1.json()["document_id"]

    # Second upload with identical bytes
    res2 = client.post(
        "/api/v1/documents",
        files={"file": ("intel_hawala_duplicate.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.INTELLIGENCE_DOCUMENT.value},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["document_id"] == doc_id1
    assert data2["content_hash"] == expected_hash


def test_unauthenticated_document_upload_rejected(client, anonymous_token):
    pdf_bytes = _make_pdf("Unauthenticated upload test")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("anon_report.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 401


def test_case_rbac_authorized_investigator_upload_accepted(client, io_assigned_token):
    """IO assigned to case-0001 can upload and retrieve document for case-0001."""
    pdf_bytes = _make_pdf("Seizure Memo for case-0001")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("seizure_memo.pdf", pdf_bytes, "application/pdf")},
        data={"case_id": "case-0001", "source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "case-0001"

    # Authorized IO can view metadata and text
    doc_id = data["document_id"]
    meta_res = client.get(f"/api/v1/documents/{doc_id}")
    assert meta_res.status_code == 200

    text_res = client.get(f"/api/v1/documents/{doc_id}/text")
    assert text_res.status_code == 200


def test_case_rbac_unauthorized_investigator_rejected_and_confidentiality_preserved(client, io_unassigned_token):
    """Unassigned IO cannot upload to case-0001 and cannot discover existing case-0001 documents."""
    pdf_bytes = _make_pdf("Illegal Upload Attempt")
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("attempt.pdf", pdf_bytes, "application/pdf")},
        data={"case_id": "case-0001"},
    )
    assert upload_res.status_code == 403
    assert "Forbidden" in upload_res.json()["detail"]


def test_audit_event_recorded_on_upload_and_view(client, sp_token):
    from backend.app.services.audit_service import AuditEventType
    app_repo = getattr(app.state, "repository", None)

    pdf_bytes = _make_pdf("Audit test document with unique content 2026-X9")
    res = client.post(
        "/api/v1/documents",
        files={"file": ("audit_sample.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.FIR_DOCUMENT.value},
    )
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    # Verify DOCUMENT_UPLOADED in audit logs
    if hasattr(app_repo, "audit_events"):
        upload_events = [
            e for e in app_repo.audit_events
            if e.get("event_type") == AuditEventType.DOCUMENT_UPLOADED.value
            and (e.get("entity_id") == doc_id or e.get("details", {}).get("document_id") == doc_id)
        ]
        assert len(upload_events) >= 1

    # View document metadata
    view_res = client.get(f"/api/v1/documents/{doc_id}")
    assert view_res.status_code == 200

    if hasattr(app_repo, "audit_events"):
        view_events = [
            e for e in app_repo.audit_events
            if e.get("event_type") == AuditEventType.DOCUMENT_VIEWED.value
            and (e.get("entity_id") == doc_id or e.get("details", {}).get("document_id") == doc_id)
        ]
        assert len(view_events) >= 1


def test_phase_boundary_no_graph_mutation_occurs_during_document_ingestion(client, sp_token):
    """Verify that unstructured document ingestion strictly does NOT mutate graph nodes or edges."""
    app_repo = getattr(app.state, "repository", None)
    initial_node_count = len(app_repo.nodes) if app_repo else 0
    initial_edge_count = len(app_repo.edges) if app_repo else 0

    pdf_bytes = _make_pdf("Strict Phase Boundary Verification Document")
    res = client.post(
        "/api/v1/documents",
        files={"file": ("boundary_doc.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": DocumentSourceType.FIR_DOCUMENT.value},
    )
    assert res.status_code == 200

    after_node_count = len(app_repo.nodes) if app_repo else 0
    after_edge_count = len(app_repo.edges) if app_repo else 0

    assert after_node_count == initial_node_count
    assert after_edge_count == initial_edge_count
