"""Tests for the isolated M2 CSV trial runner."""

import json
from pathlib import Path

from backend.app.db.ingestion.cli import OUTPUT_FILES, run_trial

FIR = """record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,vehicle_number,address,national_id
fir_001,FIR-001,2026,Central,Synthetic District,2026-08-24T14:00:00Z,theft,303,Vikram Sharma,ACCUSED,+919845012345,KA01AB1234,Synthetic Road,SYN-ID-001
"""
CDR = """record_id,caller_number,callee_number,start_time,duration_seconds,call_type,end_time,caller_imei,callee_imei,caller_subscriber_name,caller_national_id,callee_subscriber_name,callee_national_id,cell_location
cdr_001,+919845012345,9845067890,2026-08-24T14:05:00Z,60,OUTGOING,2026-08-24T14:06:00Z,IMEI-A,IMEI-B,Vikram Sharma,SYN-ID-001,,,CELL-SYN-01
"""
BANK = """record_id,utr,from_account,from_bank,to_account,to_bank,amount,currency,timestamp,from_ifsc,from_holder_name,from_holder_national_id,to_ifsc,to_holder_name,to_holder_national_id
bank_001,UTR-001,001234,Synthetic Bank,009876,Synthetic Trust,100.00,INR,2026-08-24T14:10:00Z,SBIN0001234,Vikram Sharma,SYN-ID-001,,,
"""


def make_input_dir(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("fir_records.csv").write_text(FIR, encoding="utf-8")
    root.joinpath("cdr_records.csv").write_text(CDR, encoding="utf-8")
    root.joinpath("bank_transactions.csv").write_text(BANK, encoding="utf-8")


def test_runner_writes_only_the_provided_output_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    make_input_dir(input_dir)
    outside = tmp_path / "outside.txt"
    outside.write_text("sentinel", encoding="utf-8")

    summary = run_trial(input_dir, output_dir)

    assert summary["accepted_count"] == 3
    assert summary["provenance_completeness_percent"] == 100.0
    assert sorted(path.name for path in output_dir.iterdir()) == sorted(OUTPUT_FILES)
    assert outside.read_text(encoding="utf-8") == "sentinel"
    assert not list(input_dir.glob("*.json"))


def test_runner_outputs_are_json_and_metrics_are_explicitly_unevaluated_without_ground_truth(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    make_input_dir(input_dir)

    run_trial(input_dir, output_dir)

    for filename in OUTPUT_FILES:
        json.loads(output_dir.joinpath(filename).read_text(encoding="utf-8"))
    metrics = json.loads(output_dir.joinpath("evaluation_metrics.json").read_text(encoding="utf-8"))
    assert metrics["evaluated"] is False
    assert "ground-truth" in metrics["reason"]
    assert json.loads(output_dir.joinpath("normalized_relationships.json").read_text(encoding="utf-8"))
