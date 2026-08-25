"""Tests for the synthetic intelligence-report CSV parser."""

from pathlib import Path

from backend.app.core.graph.enums import GraphRelationshipType
from backend.app.db.ingestion.parsers.intelligence import (
    parse_intelligence_csv,
    parse_intelligence_text,
)

HEADER = "record_id,report_id,report_date,source_agency,classification,subject_name,summary,alias,phone_number,national_id,organization,location"


def report_row(record_id: str, report_id: str, subject: str, alias: str = "", phone: str = "", national_id: str = "", organization: str = "") -> str:
    return ",".join([record_id, report_id, "2026-08-24T10:00:00Z", "Synthetic Intelligence Unit", "RESTRICTED", subject, "Neutral synthetic observation", alias, phone, national_id, organization, "Synthetic District"])


def test_multiple_subjects_share_one_report_and_mentions_are_neutral() -> None:
    bundle = parse_intelligence_text("\n".join([HEADER, report_row("intel_001", "RPT-001", "Vikram Sharma", "Vicky", "+91 98450-12345", "SYN-ID-001", "Synthetic Org"), report_row("intel_002", "RPT-001", "Bikram Sarma")]))
    reports = [node for node in bundle.nodes if node.entity_type.value == "IntelligenceReport"]
    mentions = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.MENTIONED_IN]
    associations = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.ASSOCIATED_WITH]
    assert len(reports) == 1
    assert len(mentions) == 2
    assert len(associations) == 1
    assert all("guilt" not in report.summary.lower() for report in reports)
    assert all("criminal" not in report.summary.lower() for report in reports)


def test_missing_optional_fields_and_alias_identity_evidence() -> None:
    bundle = parse_intelligence_text("\n".join([HEADER, report_row("intel_001", "RPT-001", "Vikram Sharma", "Vicky", "+919845012345", "SYN-ID-001"), report_row("intel_002", "RPT-002", "Other Person")]))
    people = [node for node in bundle.nodes if node.entity_type.value == "Person"]
    first = people[0]
    assert first.aliases == ["Vicky"]
    assert first.phone_numbers == ["9845012345"]
    assert first.attributes["identity_claims"][0]["alias"] == "vicky"
    assert len(people) == 2


def test_repeated_report_id_reuses_report_node() -> None:
    bundle = parse_intelligence_text("\n".join([HEADER, report_row("intel_001", "RPT-001", "Vikram Sharma", national_id="SYN-ID-001"), report_row("intel_002", "RPT-001", "Vikram Sharma", national_id="SYN-ID-001")]))
    reports = [node for node in bundle.nodes if node.entity_type.value == "IntelligenceReport"]
    people = [node for node in bundle.nodes if node.entity_type.value == "Person"]
    mentions = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.MENTIONED_IN]
    assert len(reports) == 1
    assert len(people) == 1
    assert len(mentions) == 2


def test_source_lineage_and_deterministic_ids(tmp_path: Path) -> None:
    path = tmp_path / "intelligence_records.csv"
    path.write_text("\n".join([HEADER, report_row("intel_001", "RPT-001", "Vikram Sharma", "Vicky", "+919845012345", "SYN-ID-001", "Synthetic Org")]), encoding="utf-8")
    first = parse_intelligence_csv(path, batch_id="batch_001")
    second = parse_intelligence_csv(path, batch_id="batch_001")
    assert len(first.source_records) == 1
    source_ids = {record.id for record in first.source_records}
    assert all(edge.source_record_id in source_ids for edge in first.relationships)
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.relationships] == [edge.id for edge in second.relationships]
    assert [record.id for record in first.source_records] == [record.id for record in second.source_records]
    assert all("guilt" not in str(edge.properties).lower() for edge in first.relationships)
