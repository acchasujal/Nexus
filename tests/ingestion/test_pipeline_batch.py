"""Tests for the byte-level batch pipeline."""

import pytest
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.db.ingestion.contracts import UploadedSource, SourceType, IssueSeverity

FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,national_id\n"
CDR_HEADER = "record_id,caller_number,callee_number,start_time,duration_seconds,call_type,caller_subscriber_name,caller_national_id,callee_subscriber_name,callee_national_id\n"
BANK_HEADER = "record_id,utr,from_account,from_bank,to_account,to_bank,amount,currency,timestamp,from_holder_name,from_holder_national_id,to_holder_name,to_holder_national_id\n"

def test_fir_only_bytes() -> None:
    pipeline = CsvIngestionPipeline()
    csv = FIR_HEADER + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,9999999999,NID123\n"
    source = UploadedSource(source_type=SourceType.FIR, file_name="my_fir.csv", data=csv.encode("utf-8"))
    bundle = pipeline.ingest_batch([source])
    
    assert bundle.summary.accepted_count == 1
    assert bundle.source_type == SourceType.FIR
    assert "my_fir.csv" in bundle.file_name

def test_three_source_batch() -> None:
    pipeline = CsvIngestionPipeline()
    s1 = UploadedSource(source_type=SourceType.FIR, file_name="f1.csv", data=(FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice,ACCUSED,9999999999,NID1\n").encode("utf-8"))
    s2 = UploadedSource(source_type=SourceType.CDR, file_name="c1.csv", data=(CDR_HEADER + "c1,9999999999,8888888888,2026-01-01T11:00:00Z,60,VOICE,Alice,,Bob,\n").encode("utf-8"))
    s3 = UploadedSource(source_type=SourceType.BANK_TXN, file_name="b1.csv", data=(BANK_HEADER + "b1,UTR1,A1,B1,A2,B2,100,INR,2026-01-01T12:00:00Z,Alice,NID1,Bob,NID2\n").encode("utf-8"))
    
    bundle = pipeline.ingest_batch([s1, s2, s3])
    assert bundle.summary.accepted_count == 3
    assert bundle.summary.node_created_count > 0
    assert len(bundle.batch_id) == 36  # Valid UUID

def test_invalid_utf8() -> None:
    pipeline = CsvIngestionPipeline()
    source = UploadedSource(source_type=SourceType.FIR, file_name="bad.csv", data=b"\xff\xfe\x00")
    bundle = pipeline.ingest_batch([source])
    assert bundle.summary.rejected_count == 1
    assert any(i.code == "INVALID_UTF8" for i in bundle.issues)
    assert bundle.issues[0].file_name == "bad.csv"
    assert bundle.issues[0].row_number == 1

def test_empty_csv() -> None:
    pipeline = CsvIngestionPipeline()
    source = UploadedSource(source_type=SourceType.FIR, file_name="empty.csv", data=b"")
    bundle = pipeline.ingest_batch([source])
    assert bundle.summary.rejected_count == 1
    assert any(i.code == "MISSING_HEADER" for i in bundle.issues)

def test_actual_filename_in_locator() -> None:
    pipeline = CsvIngestionPipeline()
    csv = FIR_HEADER + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,9999999999,NID123\n"
    source = UploadedSource(source_type=SourceType.FIR, file_name="custom_fir_upload.csv", data=csv.encode("utf-8"))
    bundle = pipeline.ingest_batch([source])
    assert len(bundle.source_records) == 1
    assert bundle.source_records[0].locator == "custom_fir_upload.csv:r1"

def test_exact_duplicate() -> None:
    pipeline = CsvIngestionPipeline()
    csv = FIR_HEADER + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,,\n" + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,,\n"
    source = UploadedSource(source_type=SourceType.FIR, file_name="dup.csv", data=csv.encode("utf-8"))
    bundle = pipeline.ingest_batch([source])
    assert bundle.summary.accepted_count == 1
    assert bundle.summary.duplicate_count == 1
    assert bundle.summary.rejected_count == 0
    assert any(i.code == "DUPLICATE_ROW" for i in bundle.issues)

def test_conflicting_record_id() -> None:
    pipeline = CsvIngestionPipeline()
    csv = FIR_HEADER + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,,\n" + "r1,FIR2,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,Jane Doe,ACCUSED,,\n"
    source = UploadedSource(source_type=SourceType.FIR, file_name="conf.csv", data=csv.encode("utf-8"))
    bundle = pipeline.ingest_batch([source])
    assert bundle.summary.accepted_count == 1
    assert bundle.summary.conflict_count == 1
    assert bundle.summary.rejected_count == 1
    assert any(i.code == "CONFLICTING_RECORD" for i in bundle.issues)

def test_cross_source_identity_match() -> None:
    pipeline = CsvIngestionPipeline()
    s1 = UploadedSource(source_type=SourceType.FIR, file_name="f1.csv", data=(FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice,ACCUSED,9999999999,NID1\n").encode("utf-8"))
    s2 = UploadedSource(source_type=SourceType.BANK_TXN, file_name="b1.csv", data=(BANK_HEADER + "b1,UTR1,A1,B1,A2,B2,100,INR,2026-01-01T12:00:00Z,Alice,NID1,Bob,NID2\n").encode("utf-8"))
    bundle = pipeline.ingest_batch([s1, s2])
    # Alice should be matched exactly (NID1)
    assert sum(1 for c in bundle.review_candidates if c.status.name == "MATCHED") > 0

def test_name_only_review() -> None:
    pipeline = CsvIngestionPipeline()
    s1 = UploadedSource(source_type=SourceType.FIR, file_name="f1.csv", data=(FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,,\n").encode("utf-8"))
    s2 = UploadedSource(source_type=SourceType.FIR, file_name="f2.csv", data=(FIR_HEADER + "r2,F2,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,,\n").encode("utf-8"))
    bundle = pipeline.ingest_batch([s1, s2])
    assert any(c.status.name == "REVIEW_REQUIRED" for c in bundle.review_candidates)

def test_conflicting_national_ids() -> None:
    pipeline = CsvIngestionPipeline()
    s1 = UploadedSource(source_type=SourceType.FIR, file_name="f1.csv", data=(FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,9999999999,NID1\n").encode("utf-8"))
    s2 = UploadedSource(source_type=SourceType.FIR, file_name="f2.csv", data=(FIR_HEADER + "r2,F2,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,9999999999,NID2\n").encode("utf-8"))
    bundle = pipeline.ingest_batch([s1, s2])
    assert any("national_id" in c.conflicting_fields for c in bundle.review_candidates)

def test_deterministic_repeated_upload() -> None:
    pipeline = CsvIngestionPipeline()
    csv = FIR_HEADER + "r1,FIR1,2026,S1,D1,2026-01-01T12:00:00Z,Theft,379,John Doe,ACCUSED,9999999999,NID123\n"
    s1 = UploadedSource(source_type=SourceType.FIR, file_name="my_fir.csv", data=csv.encode("utf-8"))
    bundle1 = pipeline.ingest_batch([s1])
    
    pipeline2 = CsvIngestionPipeline()
    bundle2 = pipeline2.ingest_batch([s1])
    
    assert bundle1.batch_id == bundle2.batch_id
    assert len(bundle1.nodes) == len(bundle2.nodes)
