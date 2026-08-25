"""Tests for deterministic identity indexes and claim preservation."""

from backend.app.db.ingestion.contracts import SourceType
from backend.app.db.ingestion.resolution.matcher import IdentityClaim
from backend.app.db.ingestion.resolution.registry import IdentityRegistry


def claim(record_id: str, name: str, *, source_record_id: str = "src_001", phone: str = "", vehicle: str = "", national_id: str = "", aliases: list[str] | None = None) -> IdentityClaim:
    return IdentityClaim(source_record_id=source_record_id, record_id=record_id, full_name=name, aliases=aliases or [], phone_number=phone, vehicle_number=vehicle, national_id=national_id, source_type=SourceType.FIR)


def test_registry_indexes_strong_fields_and_preserves_claim_evidence() -> None:
    registry = IdentityRegistry()
    person_id = registry.register_claim(claim("fir_001", "Vikram Sharma", phone="+91 98450-12345", vehicle="KA-01 AB-1234", national_id="SYN-ID-001", aliases=["Vicky"]))
    registry.register_claim(claim("cdr_001", "Bikram Sarma", source_record_id="src_002", phone="9845012345", national_id="SYN-ID-001", aliases=["Vicky"]), person_id=person_id)

    assert registry.by_national_id["SYN-ID-001"] == {person_id}
    assert registry.by_phone["9845012345"] == {person_id}
    assert registry.by_vehicle["KA01AB1234"] == {person_id}
    assert len(registry.get_profile(person_id).claims) == 2
    assert registry.get_profile(person_id).source_record_ids == {"src_001", "src_002"}
    assert "vicky" in registry.get_profile(person_id).aliases


def test_same_name_without_strong_identity_stays_provisional() -> None:
    registry = IdentityRegistry()
    first = registry.register_claim(claim("row_001", "Rahul Kumar"))
    second = registry.register_claim(claim("row_002", "Rahul Kumar", source_record_id="src_002"))
    assert first != second
    assert len(registry.by_name["rahul kumar"]) == 2
