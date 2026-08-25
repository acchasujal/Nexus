"""Tests for the synthetic CDR CSV parser."""

from pathlib import Path

from backend.app.core.graph.algorithms.pattern_rules import detect_communication_burst_near_event
from backend.app.core.graph.algorithms.utils import build_graph_store
from backend.app.core.graph.enums import GraphRelationshipType
from backend.app.db.ingestion.parsers.cdr import parse_cdr_csv, parse_cdr_text

HEADER = "record_id,caller_number,callee_number,start_time,duration_seconds,call_type,end_time,caller_imei,callee_imei,caller_subscriber_name,caller_national_id,callee_subscriber_name,callee_national_id,cell_location"


def cdr_row(record_id: str, start: str = "2026-08-24T14:00:00Z", duration: str = "60", end: str = "", kyc: bool = True) -> str:
    values = [record_id, "+91 98450-12345", "98450-67890", start, duration, "OUTGOING", end, "IMEI-CALLER", "IMEI-CALLEE", "Vikram Sharma" if kyc else "", "SYN-ID-001" if kyc else "", "Bikram Sarma" if kyc else "", "SYN-ID-002" if kyc else "", "CELL-SYN-01"]
    return ",".join(values)


def test_phone_normalization_and_repeated_calls_remain_separate() -> None:
    bundle = parse_cdr_text("\n".join([HEADER, cdr_row("call_001"), cdr_row("call_002", start="2026-08-24T14:05:00Z")]))
    calls = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.COMMUNICATED_WITH]
    phones = [node for node in bundle.nodes if node.entity_type.value == "Phone"]
    assert len(calls) == 2
    assert len({call.id for call in calls}) == 2
    assert {phone.phone_number for phone in phones} == {"9845012345", "9845067890"}
    assert all(call.source_record_id for call in calls)


def test_duplicate_rows_and_invalid_values_are_rejected() -> None:
    duplicate = cdr_row("call_001")
    text = "\n".join([HEADER, duplicate, duplicate, cdr_row("bad_phone").replace("+91 98450-12345", "not-phone"), cdr_row("bad_time", start="not-a-date"), cdr_row("bad_duration", duration="-1"), cdr_row("bad_end", end="2026-08-24T13:00:00Z")])
    bundle = parse_cdr_text(text)
    assert bundle.summary.accepted_count == 1
    assert bundle.summary.duplicate_count == 1
    assert len(bundle.source_records) == 1
    assert sum(issue.code == "INVALID_CDR_ROW" for issue in bundle.issues) == 4


def test_missing_optional_kyc_creates_no_person_or_ownership_edges() -> None:
    bundle = parse_cdr_text("\n".join([HEADER, cdr_row("call_001", kyc=False)]))
    assert not [node for node in bundle.nodes if node.entity_type.value == "Person"]
    assert not [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.USED_PHONE]


def test_source_lineage_and_graphstore_metadata_compatibility() -> None:
    bundle = parse_cdr_text("\n".join([HEADER, cdr_row("call_001", end="2026-08-24T14:01:00Z", kyc=False)]))
    call = next(edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.COMMUNICATED_WITH)
    store = build_graph_store(bundle.nodes, bundle.relationships)
    stored = store.edge_index[GraphRelationshipType.COMMUNICATED_WITH.value][0]
    assert stored.properties["id"] == call.id
    assert stored.properties["source_record_id"] == bundle.source_records[0].id
    assert stored.properties["start_time"] == call.start_time
    assert stored.properties["duration_seconds"] == 60
    assert stored.properties["cell_location"] == "CELL-SYN-01"


def test_no_direct_person_to_person_cdr_edges() -> None:
    bundle = parse_cdr_text("\n".join([HEADER, cdr_row("call_001")]))
    person_ids = {node.id for node in bundle.nodes if node.entity_type.value == "Person"}
    assert not any(edge.source_id in person_ids and edge.target_id in person_ids for edge in bundle.relationships)


def test_deterministic_reingestion(tmp_path: Path) -> None:
    path = tmp_path / "cdr_records.csv"
    path.write_text("\n".join([HEADER, cdr_row("call_001")]), encoding="utf-8")
    first = parse_cdr_csv(path, batch_id="batch_001")
    second = parse_cdr_csv(path, batch_id="batch_001")
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.relationships] == [edge.id for edge in second.relationships]
    assert [record.id for record in first.source_records] == [record.id for record in second.source_records]
