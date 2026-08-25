"""End-to-end tests for the additive CSV ingestion pipeline."""

from pathlib import Path

from backend.app.core.graph.enums import GraphRelationshipType
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline

FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,vehicle_number,address,national_id"
CDR_HEADER = "record_id,caller_number,callee_number,start_time,duration_seconds,call_type,end_time,caller_imei,callee_imei,caller_subscriber_name,caller_national_id,callee_subscriber_name,callee_national_id,cell_location"
BANK_HEADER = "record_id,utr,from_account,from_bank,to_account,to_bank,amount,currency,timestamp,from_ifsc,from_holder_name,from_holder_national_id,to_ifsc,to_holder_name,to_holder_national_id"


def write_trial_files(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("fir_records.csv").write_text("\n".join([
        FIR_HEADER,
        "fir_001,FIR-001,2026,Central,Bengaluru,2026-08-24T14:00:00Z,theft,303,Vikram Sharma,ACCUSED,+91 98450-12345,KA-01-AB-1234,Synthetic Road,SYN-ID-001",
        "fir_002,FIR-001,2026,Central,Bengaluru,2026-08-24T14:00:00Z,theft,303,Unrelated Sharma,VICTIM,+91 99999-11111,,Other Road,SYN-ID-999",
        "fir_003,FIR-001,2026,Central,Bengaluru,not-a-date,theft,303,Broken Person,WITNESS,,,,SYN-ID-BROKEN",
    ]), encoding="utf-8")
    root.joinpath("cdr_records.csv").write_text("\n".join([
        CDR_HEADER,
        "cdr_001,+91 98450-12345,98450-67890,2026-08-24T14:05:00Z,60,OUTGOING,2026-08-24T14:06:00Z,IMEI-A,IMEI-B,Vikram Sharma,SYN-ID-001,, ,CELL-SYN-01",
        "cdr_001,+91 98450-12345,98450-67890,2026-08-24T14:05:00Z,60,OUTGOING,2026-08-24T14:06:00Z,IMEI-A,IMEI-B,Vikram Sharma,SYN-ID-001,, ,CELL-SYN-01",
    ]), encoding="utf-8")
    root.joinpath("bank_transactions.csv").write_text("\n".join([
        BANK_HEADER,
        "bank_001,UTR-001,001234,Synthetic Bank,009876,Synthetic Trust,100.00,INR,2026-08-24T14:10:00Z,SBIN0001234,Vikram Sharma,SYN-ID-001,,,",
    ]), encoding="utf-8")


def test_all_trial_csvs_ingest_with_identity_resolution_and_quality(tmp_path: Path) -> None:
    write_trial_files(tmp_path)
    pipeline = CsvIngestionPipeline()
    bundle = pipeline.ingest_directory(tmp_path)

    assert bundle.summary.accepted_count == 4
    assert bundle.summary.duplicate_count == 1
    assert any(issue.code == "INVALID_FIR_ROW" for issue in bundle.issues)
    assert bundle.summary.rejected_count >= 1
    assert pipeline.graph_store.nodes

    people = [node for node in bundle.nodes if node.entity_type.value == "Person"]
    vikram_people = [node for node in people if node.national_id == "SYN-ID-001"]
    unrelated_people = [node for node in people if node.national_id == "SYN-ID-999"]
    assert len(vikram_people) == 1
    assert len(unrelated_people) == 1


def test_provenance_and_referential_integrity_are_complete(tmp_path: Path) -> None:
    write_trial_files(tmp_path)
    bundle = CsvIngestionPipeline().ingest_directory(tmp_path)
    node_ids = {str(node.id) for node in bundle.nodes}
    source_ids = {str(record.id) for record in bundle.source_records}
    assert all(edge.source_id in node_ids and edge.target_id in node_ids for edge in bundle.relationships)
    assert all(edge.source_record_id in source_ids for edge in bundle.relationships)
    assert all(edge.derivation_class.value == "FACT" for edge in bundle.relationships)

    transfers = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.TRANSFERRED_FUNDS]
    assert transfers
    stored = pipeline_graph_edge(bundle, transfers[0])
    assert stored.properties["id"] == transfers[0].id
    assert stored.properties["source_record_id"] == transfers[0].source_record_id
    assert stored.properties["provenance"]


def pipeline_graph_edge(bundle, edge):
    """Build an isolated adapter view for the compatibility assertion."""
    from backend.app.db.ingestion.graph_adapter import build_m1_graph_store

    store = build_m1_graph_store(bundle.nodes, bundle.relationships)
    return store.edge_index[edge.edge_type.value][0]


def test_repeated_ingestion_has_identical_ids_and_no_database_side_effect(tmp_path: Path) -> None:
    write_trial_files(tmp_path)
    first_pipeline = CsvIngestionPipeline()
    second_pipeline = CsvIngestionPipeline()
    first = first_pipeline.ingest_directory(tmp_path)
    second = second_pipeline.ingest_directory(tmp_path)
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.relationships] == [edge.id for edge in second.relationships]
    assert [record.id for record in first.source_records] == [record.id for record in second.source_records]
    assert not hasattr(first_pipeline, "repository")
    assert not hasattr(second_pipeline, "repository")
