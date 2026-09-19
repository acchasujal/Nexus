"""tests/test_document_ingestion_a1.py

Dedicated test suite for NEXUS A1 — Document Ingestion Foundation.
Verifies the complete deterministic chain:
  Input Document (.pdf, .txt, .csv)
    ↓
  Validation & Content Integrity (SHA-256)
    ↓
  Canonical Source Record (repo.source_records)
    ↓
  Evidence Provenance & Resolution (EvidenceService)
    ↓
  A3 IntelligenceEvent Emission (DOCUMENT_INGESTED)
    ↓
  Timeline Projection (TimelineService)
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from backend.app.api.dependencies import get_principal
from backend.app.auth.principal import Principal
from backend.app.main import app
from shared.contracts.api import (
    DocumentSourceType,
    ExtractionStatus,
    IntelligenceEventType,
    UserRole,
)


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
def io_assigned_principal():
    """Investigating Officer authorized for CASE-0001 / CASE-141."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-IO-01",
            officer_id="OFFICER-DEMO-IO-01",
            email="rajesh.kumar@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def sp_principal():
    """Superintendent of Police with divisional authority."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-SP-01",
            officer_id="OFFICER-DEMO-SP-01",
            email="sp.cyber@ksp.gov.in",
            role=UserRole.SP,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def unassigned_principal():
    """Investigating Officer with no assigned cases."""
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


class TestDocumentIngestionA1:
    """A1 acceptance tests establishing the unbroken document-to-intelligence chain."""

    def test_pdf_ingestion_creates_canonical_source_record_and_event(self, client, io_assigned_principal):
        """A1-T01: Ingesting a PDF with a case ID creates both a Document and a canonical SourceRecord,
        emits a DOCUMENT_INGESTED IntelligenceEvent, and is resolvable via EvidenceService."""
        pdf_bytes = _make_pdf("Forensic Extraction from Suspect Device IMEI 861234056789012")
        case_id = "CASE-141"

        resp = client.post(
            "/documents",
            files={"file": ("device_forensics_01.pdf", pdf_bytes, "application/pdf")},
            data={"source_type": DocumentSourceType.POLICE_REPORT.value, "case_id": case_id},
        )
        assert resp.status_code == 200, resp.text
        doc_data = resp.json()
        doc_id = doc_data["document_id"]
        assert doc_id.startswith("doc-")
        assert doc_data["extraction_status"] == ExtractionStatus.SUCCESS.value

        # 1. Verify document is in repo.documents
        repo = app.state.repository
        assert doc_id in repo.documents
        assert repo.documents[doc_id]["case_id"] == case_id

        # 2. Verify canonical SourceRecord is created in repo.source_records
        assert doc_id in repo.source_records
        src_rec = repo.source_records[doc_id]
        assert src_rec["id"] == doc_id
        assert src_rec["entity_type"] == "SOURCE_RECORD"
        assert src_rec["content_hash"] == doc_data["content_hash"]
        assert src_rec["source_type"] == DocumentSourceType.POLICE_REPORT.value
        assert case_id in src_rec["case_ids"]

        # 3. Verify resolvable via EvidenceService API
        ev_resp = client.get(f"/evidence/{doc_id}")
        assert ev_resp.status_code == 200, ev_resp.text
        ev_data = ev_resp.json()
        assert ev_data["id"] == doc_id
        assert ev_data["case_id"] == case_id
        assert ev_data["provenance"]["source_id"] == doc_id

        # 4. Verify A3 IntelligenceEvent was emitted
        events = [
            e for e in repo.intelligence_events.values()
            if e.get("event_type") == IntelligenceEventType.DOCUMENT_INGESTED.value
            and e.get("source_id") == doc_id
        ]
        assert len(events) == 1
        event = events[0]
        assert event["case_id"] == case_id
        assert event["payload"]["document_id"] == doc_id
        assert event["payload"]["content_hash"] == doc_data["content_hash"]
        assert event["integrity_hash"] is not None

    def test_txt_ingestion_creates_source_record(self, client, io_assigned_principal):
        """A1-T02: Ingesting plain text document properly normalizes text and creates SourceRecord."""
        txt_content = b"Informant Report: Known syndicate meeting scheduled at Whitefield junction."
        case_id = "CASE-141"

        resp = client.post(
            "/documents",
            files={"file": ("informant_intel.txt", txt_content, "text/plain")},
            data={"source_type": DocumentSourceType.INTELLIGENCE_DOCUMENT.value, "case_id": case_id},
        )
        assert resp.status_code == 200
        doc_data = resp.json()
        doc_id = doc_data["document_id"]

        repo = app.state.repository
        assert doc_id in repo.source_records
        src = repo.source_records[doc_id]
        assert src["source_type"] == DocumentSourceType.INTELLIGENCE_DOCUMENT.value
        assert "Whitefield" in src["raw_excerpt"]

    def test_ingestion_without_case_id_unscoped(self, client, io_assigned_principal):
        """A1-T07: Ingesting without case ID creates Document and SourceRecord but skips case-bound event."""
        pdf_bytes = _make_pdf("General circular / guideline document")

        resp = client.post(
            "/documents",
            files={"file": ("general_circular.pdf", pdf_bytes, "application/pdf")},
            data={"source_type": DocumentSourceType.OTHER_DOCUMENT.value},
        )
        assert resp.status_code == 200
        doc_data = resp.json()
        doc_id = doc_data["document_id"]

        repo = app.state.repository
        assert doc_id in repo.documents
        assert doc_id in repo.source_records
        assert repo.source_records[doc_id]["case_ids"] == []

        # No DOCUMENT_INGESTED event emitted without case_id (as IntelligenceEvent requires a non-empty case_id)
        events = [
            e for e in repo.intelligence_events.values()
            if e.get("event_type") == IntelligenceEventType.DOCUMENT_INGESTED.value
            and e.get("source_id") == doc_id
        ]
        assert len(events) == 0

    def test_ingestion_deduplication_idempotency(self, client, io_assigned_principal):
        """A1-T06: Re-uploading the exact same document bytes is 100% idempotent;
        does not duplicate SourceRecord or re-emit IntelligenceEvents."""
        pdf_bytes = _make_pdf("Idempotent Test Document Content Unique 99221")
        case_id = "CASE-141"

        resp1 = client.post(
            "/documents",
            files={"file": ("unique_upload.pdf", pdf_bytes, "application/pdf")},
            data={"case_id": case_id},
        )
        assert resp1.status_code == 200
        doc_id1 = resp1.json()["document_id"]

        repo = app.state.repository
        events_count_before = sum(
            1 for e in repo.intelligence_events.values()
            if e.get("source_id") == doc_id1
        )
        assert events_count_before == 1

        # Re-upload identical file
        resp2 = client.post(
            "/documents",
            files={"file": ("unique_upload_renamed.pdf", pdf_bytes, "application/pdf")},
            data={"case_id": case_id},
        )
        assert resp2.status_code == 200
        doc_id2 = resp2.json()["document_id"]
        assert doc_id1 == doc_id2

        # Verify no second event was emitted
        events_count_after = sum(
            1 for e in repo.intelligence_events.values()
            if e.get("source_id") == doc_id1
        )
        assert events_count_after == 1

    def test_timeline_projection_of_ingested_document(self, client, io_assigned_principal):
        """A1-T05: Ingested document is projected onto the chronological timeline."""
        pdf_bytes = _make_pdf("Timeline Investigation Report 2026")
        case_id = "CASE-141"

        upload_resp = client.post(
            "/documents",
            files={"file": ("timeline_evidence.pdf", pdf_bytes, "application/pdf")},
            data={"case_id": case_id, "source_type": DocumentSourceType.POLICE_REPORT.value},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document_id"]

        tl_resp = client.get(f"/timeline?case_id={case_id}")
        assert tl_resp.status_code == 200
        raw_json = tl_resp.json()
        events = raw_json if isinstance(raw_json, list) else raw_json.get("events", [])

        # The document should appear in timeline
        matching = [e for e in events if e.get("source_id") == doc_id or doc_id in e.get("id", "")]
        assert len(matching) >= 1
        assert matching[0]["category"] == "EVIDENCE_DOCUMENT"

    def test_csv_ingestion_with_case_envelope(self, client, sp_principal):
        """A1-T08: Structured CSV ingestion accepts optional case_id envelope, tags source records,
        and emits DOCUMENT_INGESTED IntelligenceEvent."""
        cdr_csv = (
            "record_id,caller_number,callee_number,start_time,duration_seconds,call_type,end_time,caller_imei,callee_imei,caller_subscriber_name,caller_national_id,callee_subscriber_name,callee_national_id,cell_location\n"
            "cdr_a1_01,+919845011223,+919845077310,2026-03-05T02:12:44Z,96,OUTGOING,2026-03-05T02:14:20Z,IMEI-1,IMEI-2,Caller Name,ID-1,,,CELL-01\n"
        )
        case_id = "CASE-141"

        resp = client.post(
            "/ingest",
            files={"cdr": ("cdr_a1_test.csv", cdr_csv.encode("utf-8"), "text/csv")},
            data={"case_id": case_id},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] in ("COMPLETED", "COMPLETED_WITH_WARNINGS")

        repo = app.state.repository
        # Verify DOCUMENT_INGESTED event was emitted for the CSV file
        events = [
            e for e in repo.intelligence_events.values()
            if e.get("event_type") == IntelligenceEventType.DOCUMENT_INGESTED.value
            and e.get("case_id") == case_id
            and "cdr_a1_test.csv" in str(e.get("payload", {}))
        ]
        assert len(events) >= 1

    def test_corrupted_pdf_extraction_resilience(self, client, io_assigned_principal):
        """A1-T10: Malformed/corrupted PDF bytes are quarantined with status=FAILED,
        creating a SourceRecord indicating failure without crashing the pipeline."""
        corrupted_bytes = b"%PDF-1.4 completely corrupt content not valid pdf"
        case_id = "CASE-141"

        resp = client.post(
            "/documents",
            files={"file": ("corrupted_report.pdf", corrupted_bytes, "application/pdf")},
            data={"case_id": case_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["extraction_status"] == ExtractionStatus.FAILED.value
        doc_id = data["document_id"]

        repo = app.state.repository
        assert doc_id in repo.documents
        assert doc_id in repo.source_records
        assert repo.source_records[doc_id]["attributes"]["extraction_status"] == ExtractionStatus.FAILED.value

    def test_unauthorized_case_upload_rejected(self, client, unassigned_principal):
        """A1-T09: Uploading a document with an unauthorized case_id returns HTTP 403."""
        pdf_bytes = _make_pdf("Confidential case document")
        case_id = "CASE-141"

        resp = client.post(
            "/documents",
            files={"file": ("unauthorized.pdf", pdf_bytes, "application/pdf")},
            data={"case_id": case_id},
        )
        assert resp.status_code == 403
