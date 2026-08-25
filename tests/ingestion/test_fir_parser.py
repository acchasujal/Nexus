"""Tests for the synthetic FIR CSV parser."""

from pathlib import Path

from backend.app.core.graph.enums import GraphRelationshipType
from backend.app.db.ingestion.parsers.fir import parse_fir_csv, parse_fir_text

HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,vehicle_number,address,national_id"


def row(record_id: str, fir: str, name: str, role: str, phone: str = "", vehicle: str = "", national_id: str = "") -> str:
    return f"{record_id},{fir},2026,Central Station,Bengaluru,2026-08-24T14:00:00Z,theft,303,{name},{role},{phone},{vehicle},Sector 1,{national_id}"


def test_case_reuse_role_mapping_and_optional_normalization() -> None:
    text = "\n".join([
        HEADER,
        row("fir_001", "FIR-001", "Vikram Sharma", "ACCUSED", "+91 98450-12345", "ka-01 ab-1234", "SYN-ID-001"),
        row("fir_002", "FIR-001", "Bikram Sarma", "VICTIM", "", "", ""),
        row("fir_003", "FIR-001", "V. Sharma", "COMPLAINANT", "", "", ""),
        row("fir_004", "FIR-002", "Other Person", "WITNESS"),
    ])

    bundle = parse_fir_text(text, batch_id="batch_001")
    cases = [node for node in bundle.nodes if node.entity_type.value == "Case"]
    relationships = bundle.relationships

    assert len(cases) == 2
    assert {edge.edge_type for edge in relationships} >= {
        GraphRelationshipType.ACCUSED_IN,
        GraphRelationshipType.VICTIM_IN,
        GraphRelationshipType.COMPLAINANT_IN,
        GraphRelationshipType.WITNESS_IN,
        GraphRelationshipType.USED_PHONE,
        GraphRelationshipType.USED_VEHICLE,
    }
    phones = [node for node in bundle.nodes if node.entity_type.value == "Phone"]
    vehicles = [node for node in bundle.nodes if node.entity_type.value == "Vehicle"]
    assert phones[0].phone_number == "9845012345"
    assert vehicles[0].registration_number == "KA01AB1234"
    assert bundle.summary.accepted_count == 4


def test_source_records_and_relationship_provenance_are_complete() -> None:
    bundle = parse_fir_text(
        "\n".join([HEADER, row("fir_001", "FIR-001", "Vikram Sharma", "ACCUSED", "+919845012345", "KA01AB1234", "SYN-ID-001")]),
        batch_id="batch_001",
    )
    source_ids = {record.id for record in bundle.source_records}
    assert len(source_ids) == 1
    assert all(edge.source_record_id in source_ids for edge in bundle.relationships)
    assert bundle.source_records[0].raw_excerpt


def test_missing_optional_fields_do_not_create_links() -> None:
    bundle = parse_fir_text("\n".join([HEADER, row("fir_001", "FIR-001", "Vikram Sharma", "ACCUSED")]))
    assert not [node for node in bundle.nodes if node.entity_type.value in {"Phone", "Vehicle"}]
    assert not [edge for edge in bundle.relationships if edge.edge_type in {GraphRelationshipType.USED_PHONE, GraphRelationshipType.USED_VEHICLE}]


def test_unknown_role_and_invalid_timestamp_are_rejected() -> None:
    unknown = parse_fir_text("\n".join([HEADER, row("fir_001", "FIR-001", "Vikram Sharma", "UNKNOWN")]))
    invalid = parse_fir_text("\n".join([HEADER, row("fir_002", "FIR-002", "Vikram Sharma", "ACCUSED").replace("2026-08-24T14:00:00Z", "not-a-date")]))
    assert any(issue.code == "UNKNOWN_ROLE" for issue in unknown.issues)
    assert any(issue.code == "INVALID_FIR_ROW" for issue in invalid.issues)
    assert unknown.summary.accepted_count == 0
    assert invalid.summary.accepted_count == 0


def test_deterministic_reingestion_from_file(tmp_path: Path) -> None:
    path = tmp_path / "fir_records.csv"
    path.write_text("\n".join([HEADER, row("fir_001", "FIR-001", "Vikram Sharma", "ACCUSED", "+919845012345", "KA01AB1234", "SYN-ID-001")]), encoding="utf-8")

    first = parse_fir_csv(path, batch_id="batch_001")
    second = parse_fir_csv(path, batch_id="batch_001")

    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.relationships] == [edge.id for edge in second.relationships]
    assert [record.id for record in first.source_records] == [record.id for record in second.source_records]
