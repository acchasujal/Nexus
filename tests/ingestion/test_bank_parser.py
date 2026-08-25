"""Tests for the synthetic bank transaction CSV parser."""

from pathlib import Path

from backend.app.core.graph.algorithms.pattern_rules import (
    detect_circular_repeated_financial_flow,
)
from backend.app.core.graph.algorithms.utils import build_graph_store
from backend.app.core.graph.enums import GraphRelationshipType
from backend.app.db.ingestion.parsers.bank import parse_bank_csv, parse_bank_text

HEADER = "record_id,utr,from_account,from_bank,to_account,to_bank,amount,currency,timestamp,from_ifsc,from_holder_name,from_holder_national_id,to_ifsc,to_holder_name,to_holder_national_id"


def bank_row(record_id: str, utr: str, source: str = "001234", target: str = "009876", amount: str = "100.50", currency: str = "INR", from_kyc: bool = False, to_kyc: bool = False) -> str:
    values = [record_id, utr, source, "Synthetic Bank", target, "Synthetic Trust", amount, currency, "2026-08-24T14:00:00Z", "SBIN0001234" if from_kyc else "", "Synthetic Sender" if from_kyc else "", "SYN-ID-FROM" if from_kyc else "", "HDFC0005678" if to_kyc else "", "Synthetic Receiver" if to_kyc else "", "SYN-ID-TO" if to_kyc else ""]
    return ",".join(values)


def test_leading_zero_amount_and_transfer_fields() -> None:
    bundle = parse_bank_text("\n".join([HEADER, bank_row("txn_001", "UTR-001", from_kyc=True, to_kyc=True)]))
    accounts = [node for node in bundle.nodes if node.entity_type.value == "Account"]
    transfer = next(edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.TRANSFERRED_FUNDS)
    assert {account.account_number for account in accounts} == {"001234", "009876"}
    assert transfer.properties["amount"] == 100.50 or str(transfer.properties["amount"]) == "100.50"
    assert transfer.properties["currency"] == "INR"
    assert transfer.properties["utr"] == "UTR-001"
    assert transfer.derivation_class.value == "FACT"


def test_invalid_amount_currency_and_duplicate_utr() -> None:
    text = "\n".join([HEADER, bank_row("txn_001", "UTR-001"), bank_row("txn_002", "UTR-001"), bank_row("txn_003", "UTR-003", amount="-1"), bank_row("txn_004", "UTR-004", currency="RUPEES")])
    bundle = parse_bank_text(text)
    assert bundle.summary.accepted_count == 1
    assert bundle.summary.duplicate_count == 0
    assert any(issue.code == "DUPLICATE_UTR" for issue in bundle.issues)
    assert sum(issue.code == "INVALID_BANK_ROW" for issue in bundle.issues) == 2


def test_repeated_transfers_remain_distinct_and_have_lineage() -> None:
    bundle = parse_bank_text("\n".join([HEADER, bank_row("txn_001", "UTR-001"), bank_row("txn_002", "UTR-002")]))
    transfers = [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.TRANSFERRED_FUNDS]
    assert len(transfers) == 2
    assert len({edge.id for edge in transfers}) == 2
    source_ids = {record.id for record in bundle.source_records}
    assert all(edge.source_record_id in source_ids for edge in transfers)


def test_circular_flow_is_compatible_with_financial_pattern_rule() -> None:
    rows = [bank_row("txn_001", "UTR-001", "001", "002"), bank_row("txn_002", "UTR-002", "002", "003"), bank_row("txn_003", "UTR-003", "003", "001")]
    bundle = parse_bank_text("\n".join([HEADER, *rows]))
    store = build_graph_store(bundle.nodes, bundle.relationships)
    findings = detect_circular_repeated_financial_flow(store)
    assert any(len(f.entity_ids) == 3 for f in findings)
    assert all("fraud" not in f.explanation.lower() and "suspicious" not in f.explanation.lower() for f in findings)


def test_missing_kyc_does_not_create_ownership_edges() -> None:
    bundle = parse_bank_text("\n".join([HEADER, bank_row("txn_001", "UTR-001", from_kyc=False, to_kyc=False)]))
    assert not [node for node in bundle.nodes if node.entity_type.value == "Person"]
    assert not [edge for edge in bundle.relationships if edge.edge_type is GraphRelationshipType.OWNS_ACCOUNT]


def test_deterministic_reingestion(tmp_path: Path) -> None:
    path = tmp_path / "bank_transactions.csv"
    path.write_text("\n".join([HEADER, bank_row("txn_001", "UTR-001", from_kyc=True)]), encoding="utf-8")
    first = parse_bank_csv(path, batch_id="batch_001")
    second = parse_bank_csv(path, batch_id="batch_001")
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [edge.id for edge in first.relationships] == [edge.id for edge in second.relationships]
    assert [record.id for record in first.source_records] == [record.id for record in second.source_records]
