"""tests/test_surveillance_ingestion_p1d.py

Comprehensive Phase P1-D Test Suite:
Dedicated Surveillance Report Ingestion.

Validates:
  1. SourceType enum includes SURVEILLANCE_REPORT
  2. Valid surveillance record parsing and bundle mapping
  3. Strict invalid record rejection (missing required columns, empty values, malformed timestamps)
  4. Deterministic normalization (phone, vehicle registration, ISO UTC timestamps)
  5. Entity resolution with existing multi-attribute registry
  6. Ambiguous entity handling (flags REVIEW_REQUIRED, zero arbitrary fusion)
  7. Deterministic relationship mapping (SEEN_AT, USED_VEHICLE, USED_PHONE, ASSOCIATED_WITH)
  8. Zero unsupported inference (no OWNS, no ACCUSED_IN, no guilt scores, no proximity links)
  9. Full provenance preservation with report_id, observation_id, and source_record_id
  10. Idempotency on repeated report ingestion
  11. Duplicate observation row quarantine
  12. Edge corroboration without duplicate edge creation
  13. Atomicity / failure rollback on invalid bundles
  14. Server-side RBAC enforcement
  15. Audit event logging (UPLOADED, INGESTED, INGESTION_FAILED)
  16. Zero LLM calls in the entire ingestion pipeline
"""

from __future__ import annotations

from datetime import timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_principal
from backend.app.auth.policy import Principal
from backend.app.core.graph.enums import (
    DerivationClass,
    GraphEntityType,
    GraphRelationshipType,
    ResolutionStatus,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.contracts import (
    IngestionBundle,
    SourceType,
    UploadedSource,
)
from backend.app.db.ingestion.mappers.surveillance import map_surveillance_bundle
from backend.app.db.ingestion.parsers.surveillance import (
    parse_surveillance_text,
)
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.main import app
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.ingestion_service import IngestionService
from shared.contracts.api import BatchStatus, UserRole


SAMPLE_SURVEILLANCE_CSV = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary,source_agency,officer_badge,vehicle_registration,phone_number,source_reference,national_id,organization
SURV-001,REP-2026-01,FIR-2026-495,2026-09-14T21:10:00Z,Ramesh Hegde,PHYSICAL_SIGHTING,MG Road Bengaluru,Subject observed entering black sedan,CCB Bengaluru,BLR-7481,KA-01-AB-4721,+919876543210,SURV-LOG-17,NID-IND-88412,Apex Logistics
SURV-002,REP-2026-01,FIR-2026-495,2026-09-14T21:30:00Z,Suresh Kumar,ELECTRONIC_INTERCEPT,Indiranagar Bengaluru,Subject pinged near cell tower,CCB Bengaluru,BLR-7481,,+919876543211,SURV-LOG-18,,Apex Logistics
"""

FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,national_id\n"


@pytest.fixture
def repo():
    return InMemoryBackendRepository()


@pytest.fixture
def graph_repo(repo):
    return GraphRepository(repo.to_graph_store())


@pytest.fixture
def audit_service(repo):
    return AuditService(repo)


@pytest.fixture
def pipeline():
    return CsvIngestionPipeline()


@pytest.fixture
def ingestion_service(repo, graph_repo, audit_service, pipeline):
    return IngestionService(repo, graph_repo, audit_service, pipeline)


# ── Test 1: SourceType Inclusion ─────────────────────────────────────────────

def test_source_type_includes_surveillance_report():
    """Verify SURVEILLANCE_REPORT is a first-class member of SourceType enum without breaking existing types."""
    assert hasattr(SourceType, "SURVEILLANCE_REPORT")
    assert SourceType.SURVEILLANCE_REPORT.value == "SURVEILLANCE_REPORT"
    # Ensure existing types remain intact
    assert SourceType.FIR.value == "FIR"
    assert SourceType.CDR.value == "CDR"
    assert SourceType.BANK_TXN.value == "BANK_TXN"
    assert SourceType.INTEL_REPORT.value == "INTEL_REPORT"


# ── Test 2: Valid Surveillance Record Parsing & Mapping ──────────────────────

def test_valid_surveillance_parsing_and_mapping():
    """Test parsing and mapping valid surveillance CSV data into graph entities and relationships."""
    parsed = parse_surveillance_text(SAMPLE_SURVEILLANCE_CSV, batch_id="batch-surv-01")
    assert len(parsed.rows) == 2
    assert len(parsed.issues) == 0

    first = parsed.rows[0]
    assert first["record_id"] == "SURV-001"
    assert first["report_id"] == "REP-2026-01"
    assert first["case_id"] == "FIR-2026-495"
    assert first["subject_name"] == "Ramesh Hegde"
    assert first["observation_type"] == "PHYSICAL_SIGHTING"
    assert first["vehicle_registration"] == "KA01AB4721"  # Normalized
    assert first["phone_number"] == "9876543210"

    bundle: IngestionBundle = map_surveillance_bundle(parsed)
    node_types = {n.entity_type for n in bundle.nodes}
    assert GraphEntityType.PERSON in node_types
    assert GraphEntityType.LOCATION in node_types
    assert GraphEntityType.VEHICLE in node_types
    assert GraphEntityType.PHONE in node_types
    assert GraphEntityType.ORGANIZATION in node_types

    edge_types = {e.edge_type for e in bundle.relationships}
    assert GraphRelationshipType.SEEN_AT in edge_types
    assert GraphRelationshipType.USED_VEHICLE in edge_types
    assert GraphRelationshipType.USED_PHONE in edge_types
    assert GraphRelationshipType.ASSOCIATED_WITH in edge_types


# ── Test 3: Invalid Record Rejection ─────────────────────────────────────────

def test_missing_required_columns_rejected():
    """Missing required columns must produce fatal parse issues."""
    invalid_csv = """record_id,case_id,location
SURV-001,FIR-2026-495,MG Road
"""
    parsed = parse_surveillance_text(invalid_csv, batch_id="batch-surv-invalid")
    assert any(i.code == "MISSING_REQUIRED_COLUMN" for i in parsed.issues)
    assert len(parsed.rows) == 0


def test_empty_required_values_quarantined():
    """Rows with empty required fields (e.g. missing report_id or subject_name) are quarantined."""
    csv_empty_fields = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary
SURV-001,,FIR-2026-495,2026-09-14T21:10:00Z,Ramesh Hegde,PHYSICAL_SIGHTING,MG Road,Observed entering vehicle
SURV-002,REP-01,FIR-2026-495,2026-09-14T21:10:00Z,,PHYSICAL_SIGHTING,MG Road,Observed entering vehicle
"""
    parsed = parse_surveillance_text(csv_empty_fields, batch_id="batch-surv-empty")
    assert len(parsed.rows) == 0
    assert len(parsed.issues) >= 2


def test_malformed_timestamp_quarantined():
    """Rows with unparseable timestamps must be rejected."""
    csv_bad_time = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary
SURV-001,REP-01,FIR-2026-495,not-a-timestamp,Ramesh Hegde,PHYSICAL_SIGHTING,MG Road,Observed entering vehicle
"""
    parsed = parse_surveillance_text(csv_bad_time, batch_id="batch-bad-time")
    assert len(parsed.rows) == 0
    assert any(i.code == "INVALID_TIMESTAMP" for i in parsed.issues)


# ── Test 4: Normalization ────────────────────────────────────────────────────

def test_surveillance_normalization():
    """Verify phone, vehicle, and timestamp normalization."""
    csv_unnormalized = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary,vehicle_registration,phone_number
SURV-001,REP-01,FIR-2026-495,2026-09-14 21:10:00+05:30, Ramesh Hegde ,PHYSICAL_SIGHTING, MG Road Bengaluru ,Observed entering vehicle,ka-01 ab 4721,9876543210
"""
    parsed = parse_surveillance_text(csv_unnormalized, batch_id="batch-norm")
    assert len(parsed.rows) == 1
    rec = parsed.rows[0]
    assert rec["vehicle_registration"] == "KA01AB4721"
    assert rec["phone_number"] == "9876543210"
    assert rec["subject_name"] == "Ramesh Hegde"
    assert rec["location"] == "MG Road Bengaluru"
    assert rec["observed_at"].tzinfo == timezone.utc


# ── Test 5 & 6: Entity Resolution & Ambiguity Handling ────────────────────────

def test_entity_resolution_with_existing_registry(pipeline):
    """When a surveillance report contains strong claims (NID/phone), it resolves to existing canonical entity."""
    fir_csv = FIR_HEADER + "FIR-001,495,2026,Cubbon Park,Central,2026-09-01T10:00:00Z,Theft,379,Ramesh Hegde,ACCUSED,9876543210,NID-IND-88412\n"
    fir_source = UploadedSource(source_type=SourceType.FIR, file_name="fir.csv", data=fir_csv.encode("utf-8"))
    fir_bundle = pipeline.ingest_batch([fir_source])
    fir_person_id = next(n.id for n in fir_bundle.nodes if n.entity_type == GraphEntityType.PERSON)

    # Now ingest surveillance report with matching NID and phone
    surv_source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surv.csv", data=SAMPLE_SURVEILLANCE_CSV.encode("utf-8"))
    surv_bundle = pipeline.ingest_batch([surv_source])
    surv_person_id = next(n.id for n in surv_bundle.nodes if n.entity_type == GraphEntityType.PERSON and (getattr(n, "full_name", "") == "Ramesh Hegde" or n.properties.get("name") == "Ramesh Hegde"))

    # Should resolve to the same canonical person ID
    assert surv_person_id == fir_person_id


def test_ambiguous_entity_does_not_arbitrarily_fuse(pipeline):
    """When a surveillance report has only a common name with no NID or phone, it does NOT arbitrarily fuse."""
    fir_csv = FIR_HEADER + "FIR-001,495,2026,Cubbon Park,Central,2026-09-01T10:00:00Z,Theft,379,Ramesh Hegde,ACCUSED,9876543210,NID-IND-88412\n"
    fir_source = UploadedSource(source_type=SourceType.FIR, file_name="fir.csv", data=fir_csv.encode("utf-8"))
    fir_bundle = pipeline.ingest_batch([fir_source])
    fir_person_id = next(n.id for n in fir_bundle.nodes if n.entity_type == GraphEntityType.PERSON)

    # Surveillance report with Ramesh Hegde but NO NID and NO phone
    surv_csv = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary
SURV-099,REP-2026-09,FIR-2026-495,2026-09-15T10:00:00Z,Ramesh Hegde,PHYSICAL_SIGHTING,Koramangala,Subject spotted walking
"""
    surv_source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surv.csv", data=surv_csv.encode("utf-8"))
    surv_bundle = pipeline.ingest_batch([surv_source])
    surv_person_id = next(n.id for n in surv_bundle.nodes if n.entity_type == GraphEntityType.PERSON and (getattr(n, "full_name", "") == "Ramesh Hegde" or n.properties.get("name") == "Ramesh Hegde"))

    # Must NOT fuse arbitrarily
    assert surv_person_id != fir_person_id
    # Must flag for human review
    assert any(cand.status == ResolutionStatus.REVIEW_REQUIRED for cand in surv_bundle.review_candidates)


# ── Test 7: Relationship Mapping ─────────────────────────────────────────────

def test_relationship_mapping_supported_types():
    """Verify only established relationship types are produced from surveillance records."""
    parsed = parse_surveillance_text(SAMPLE_SURVEILLANCE_CSV, batch_id="batch-rel")
    bundle = map_surveillance_bundle(parsed)

    allowed_types = {GraphRelationshipType.SEEN_AT, GraphRelationshipType.USED_VEHICLE, GraphRelationshipType.USED_PHONE, GraphRelationshipType.ASSOCIATED_WITH}
    for edge in bundle.relationships:
        assert edge.edge_type in allowed_types, f"Unexpected edge type: {edge.edge_type}"
        assert edge.derivation_class == DerivationClass.FACT


# ── Test 8: Zero Unsupported Inference ───────────────────────────────────────

def test_zero_unsupported_inference():
    """Surveillance ingestion must NOT infer OWNS, ACCUSED_IN, COMMITTED, or proximity associations."""
    parsed = parse_surveillance_text(SAMPLE_SURVEILLANCE_CSV, batch_id="batch-inference")
    bundle = map_surveillance_bundle(parsed)

    for edge in bundle.relationships:
        assert edge.edge_type != GraphRelationshipType.ACCUSED_IN
        assert edge.edge_type != GraphRelationshipType.OWNS_VEHICLE
        assert edge.edge_type != GraphRelationshipType.CO_ACCUSED_WITH

    # Ensure Ramesh Hegde and Suresh Kumar are NOT connected merely by appearing in the same report
    ramesh_node = next(n for n in bundle.nodes if getattr(n, "full_name", "") == "Ramesh Hegde" or n.properties.get("name") == "Ramesh Hegde")
    suresh_node = next(n for n in bundle.nodes if getattr(n, "full_name", "") == "Suresh Kumar" or n.properties.get("name") == "Suresh Kumar")
    direct_edges = [
        e for e in bundle.relationships
        if (e.source_id == ramesh_node.id and e.target_id == suresh_node.id)
        or (e.source_id == suresh_node.id and e.target_id == ramesh_node.id)
    ]
    assert len(direct_edges) == 0, "No unsupported proximity association between distinct report subjects"


# ── Test 9: Provenance Preservation ──────────────────────────────────────────

def test_provenance_preservation():
    """Every edge produced from surveillance records must cite report ID, observation ID, and source record ID."""
    parsed = parse_surveillance_text(SAMPLE_SURVEILLANCE_CSV, batch_id="batch-prov")
    bundle = map_surveillance_bundle(parsed)

    for edge in bundle.relationships:
        assert edge.provenance is not None
        assert edge.provenance.source_type == "SURVEILLANCE_REPORT"
        assert edge.provenance.source_record_id is not None
        assert edge.provenance.derivation_method == "SURVEILLANCE_OBSERVATION"
        assert "REP-2026-01" in edge.properties.get("report_id", "")
        assert edge.properties.get("observation_id") in ("SURV-001", "SURV-002")


# ── Test 10: Idempotency on Repeated Ingestion ────────────────────────────────

@pytest.mark.anyio
async def test_idempotent_repeated_ingestion(ingestion_service, repo):
    """Ingesting the exact same surveillance CSV twice produces identical graph topology with zero duplicate nodes or edges."""
    data = SAMPLE_SURVEILLANCE_CSV.encode("utf-8")
    source1 = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surveillance_records.csv", data=data)
    resp1 = await ingestion_service.ingest_files("officer-01", "SP", [source1])
    assert resp1.status == BatchStatus.COMPLETED
    nodes_count_1 = len(repo.nodes)
    edges_count_1 = len(repo.edges)

    source2 = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surveillance_records.csv", data=data)
    resp2 = await ingestion_service.ingest_files("officer-01", "SP", [source2])
    assert resp2.status == BatchStatus.COMPLETED
    assert len(repo.nodes) == nodes_count_1
    assert len(repo.edges) == edges_count_1
    assert resp2.summary.nodes_reused > 0


# ── Test 11: Duplicate Observation Quarantine ────────────────────────────────

def test_duplicate_rows_quarantined():
    """Duplicate observation records within the same CSV file are quarantined."""
    dup_csv = f"{SAMPLE_SURVEILLANCE_CSV}{SAMPLE_SURVEILLANCE_CSV.splitlines()[1]}\n"
    parsed = parse_surveillance_text(dup_csv, batch_id="batch-dup")
    assert len(parsed.rows) == 2
    assert any(i.code == "DUPLICATE_ROW" for i in parsed.issues)


# ── Test 12: Corroboration of Existing Edge ──────────────────────────────────

@pytest.mark.anyio
async def test_corroboration_of_existing_edge(ingestion_service, repo):
    """When a new surveillance report confirms an existing SEEN_AT edge, it adds corroboration rather than duplicating the edge."""
    # First report places Ramesh at MG Road
    csv1 = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary,national_id
SURV-001,REP-01,FIR-2026-495,2026-09-14T21:10:00Z,Ramesh Hegde,PHYSICAL_SIGHTING,MG Road Bengaluru,Observed entering cafe,NID-IND-88412
"""
    s1 = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surv1.csv", data=csv1.encode("utf-8"))
    await ingestion_service.ingest_files("officer-01", "SP", [s1])

    seen_at_edges_initial = [e for e in repo.edges if e.get("edge_type") == "SEEN_AT"]
    assert len(seen_at_edges_initial) == 1

    # Second report on a different day also observes Ramesh Hegde at MG Road
    csv2 = """record_id,report_id,case_id,observed_at,subject_name,observation_type,location,summary,national_id
SURV-002,REP-02,FIR-2026-495,2026-09-15T18:00:00Z,Ramesh Hegde,PHYSICAL_SIGHTING,MG Road Bengaluru,Observed leaving cafe,NID-IND-88412
"""
    s2 = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surv2.csv", data=csv2.encode("utf-8"))
    await ingestion_service.ingest_files("officer-01", "SP", [s2])

    seen_at_edges_after = [e for e in repo.edges if e.get("edge_type") == "SEEN_AT"]
    # Total count must NOT increase
    assert len(seen_at_edges_after) == 1
    # Corroborating evidence must be attached
    corroborating = seen_at_edges_after[0].get("properties", {}).get("corroborating_evidence", [])
    assert len(corroborating) >= 1


# ── Test 13: Failure Rollback / Atomicity ─────────────────────────────────────

@pytest.mark.anyio
async def test_fatal_error_prevents_partial_writes(ingestion_service, repo):
    """Fatal parse errors fail cleanly and record INGESTION_FAILED without creating partial graph state."""
    initial_node_count = len(repo.nodes)
    initial_edge_count = len(repo.edges)

    fatal_csv = """record_id,case_id
SURV-001,FIR-2026-495
"""
    source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="fatal.csv", data=fatal_csv.encode("utf-8"))
    resp = await ingestion_service.ingest_files("officer-01", "SP", [source])

    assert resp.status == BatchStatus.FAILED
    assert len(repo.nodes) == initial_node_count
    assert len(repo.edges) == initial_edge_count


# ── Test 14: Server-Side RBAC Enforcement ────────────────────────────────────

def test_rbac_sp_or_supervisor_required():
    """Verify role requirements for ingestion API: Investigator gets 403."""
    def override_investigator():
        return Principal(user_id="io-1", email="io@mha.gov.in", role=UserRole.INVESTIGATOR)

    app.dependency_overrides[get_principal] = override_investigator
    try:
        client = TestClient(app)
        res = client.post(
            "/api/v1/ingest",
            files={"surveillance": ("surv.csv", b"record_id\n1", "text/csv")},
        )
        assert res.status_code == 403
        assert "Forbidden" in res.json().get("detail", "")
    finally:
        app.dependency_overrides.pop(get_principal, None)


# ── Test 15: Audit Event Emission ────────────────────────────────────────────

@pytest.mark.anyio
async def test_surveillance_audit_events(ingestion_service, repo):
    """Verify SURVEILLANCE_REPORT_UPLOADED and SURVEILLANCE_REPORT_INGESTED audit events are recorded."""
    data = SAMPLE_SURVEILLANCE_CSV.encode("utf-8")
    source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surveillance_records.csv", data=data)
    await ingestion_service.ingest_files("officer-42", "SP", [source])

    event_types = [e.get("event_type") for e in repo.audit_events]
    assert AuditEventType.SURVEILLANCE_REPORT_UPLOADED.value in event_types
    assert AuditEventType.SURVEILLANCE_REPORT_INGESTED.value in event_types

    uploaded_event = next(e for e in repo.audit_events if e.get("event_type") == AuditEventType.SURVEILLANCE_REPORT_UPLOADED.value)
    assert uploaded_event.get("actor_id") == "officer-42"
    assert "surveillance_records.csv" in str(uploaded_event.get("details"))


@pytest.mark.anyio
async def test_surveillance_failed_audit_event(ingestion_service, repo):
    """Verify SURVEILLANCE_REPORT_INGESTION_FAILED audit event on fatal parse error."""
    fatal_csv = """record_id,case_id
SURV-001,FIR-2026-495
"""
    source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="fatal.csv", data=fatal_csv.encode("utf-8"))
    await ingestion_service.ingest_files("officer-42", "SP", [source])

    event_types = [e.get("event_type") for e in repo.audit_events]
    assert AuditEventType.SURVEILLANCE_REPORT_INGESTION_FAILED.value in event_types


# ── Test 16: Zero LLM Calls Invariant ────────────────────────────────────────

@pytest.mark.anyio
async def test_zero_llm_calls_in_surveillance_ingestion(ingestion_service):
    """Ensure no LLM client is invoked during surveillance report ingestion."""
    with patch("backend.app.ai.llm_client.get_llm_client", MagicMock(side_effect=RuntimeError("LLM should not be called"))):
        data = SAMPLE_SURVEILLANCE_CSV.encode("utf-8")
        source = UploadedSource(source_type=SourceType.SURVEILLANCE_REPORT, file_name="surveillance_records.csv", data=data)
        resp = await ingestion_service.ingest_files("officer-01", "SP", [source])
        assert resp.status == BatchStatus.COMPLETED
