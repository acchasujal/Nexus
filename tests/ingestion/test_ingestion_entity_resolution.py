"""Tests for conservative ingestion-time entity resolution."""

from pathlib import Path

from backend.app.core.graph.enums import ResolutionStatus
from backend.app.db.ingestion.contracts import SourceType
from backend.app.db.ingestion.resolution.matcher import IdentityClaim, decide_candidates
from backend.app.db.ingestion.resolution.evaluator import evaluate_ground_truth
from backend.app.db.ingestion.resolution.registry import IdentityRegistry


def make_claim(record_id: str, name: str, *, source_record_id: str, phone: str = "", vehicle: str = "", address: str = "", national_id: str = "", aliases: list[str] | None = None) -> IdentityClaim:
    return IdentityClaim(source_record_id=source_record_id, record_id=record_id, full_name=name, aliases=aliases or [], phone_number=phone, vehicle_number=vehicle, address=address, national_id=national_id, source_type=SourceType.CDR)


def test_name_only_and_phonetic_name_only_require_review() -> None:
    registry = IdentityRegistry()
    registry.register_claim(make_claim("base", "Vikram Sharma", source_record_id="src_base"))
    exact = decide_candidates(registry, make_claim("incoming", "Vikram Sharma", source_record_id="src_in"))[0]
    phonetic = decide_candidates(registry, make_claim("incoming2", "Bikram Sarma", source_record_id="src_in2"))[0]
    assert exact.status is ResolutionStatus.REVIEW_REQUIRED
    assert phonetic.status is ResolutionStatus.REVIEW_REQUIRED
    assert not exact.auto_link_allowed
    assert exact.supporting_source_record_ids == ["src_base"]


def test_phone_only_review() -> None:
    registry = IdentityRegistry()
    registry.register_claim(make_claim("base", "Vikram Sharma", source_record_id="src_base", phone="+919845012345"))
    decisions = decide_candidates(registry, make_claim("in", "Unknown User", source_record_id="src_in", phone="+919845012345"))
    assert decisions[0].status is ResolutionStatus.REVIEW_REQUIRED
    assert not decisions[0].auto_link_allowed


def test_missing_identity_fields_does_not_match() -> None:
    registry = IdentityRegistry()
    registry.register_claim(make_claim("base", "", source_record_id="src_base"))
    decisions = decide_candidates(registry, make_claim("in", "", source_record_id="src_in"))
    assert not decisions
    

def test_same_name_hard_negative_with_different_nids() -> None:
    registry = IdentityRegistry()
    registry.register_claim(make_claim("base", "Vikram Sharma", source_record_id="src_base", national_id="NID-001"))
    decisions = decide_candidates(registry, make_claim("in", "Vikram Sharma", source_record_id="src_in", national_id="NID-002"))
    assert decisions[0].status is ResolutionStatus.NOT_MATCHED
    assert not decisions[0].auto_link_allowed


def test_conflicting_national_id_does_not_match() -> None:
    registry = IdentityRegistry()
    registry.register_claim(make_claim("base", "Vikram Sharma", source_record_id="src_base", phone="+91 98450-12345", national_id="NID-001"))
    decisions = decide_candidates(registry, make_claim("in", "Bikram Sarma", source_record_id="src_in", phone="+91 98450-12345", national_id="NID-002"))
    assert decisions[0].status is ResolutionStatus.NOT_MATCHED
    assert not decisions[0].auto_link_allowed


def test_positive_resolution_across_variants() -> None:
    # Vikram Sharma (FIR), Bikram Sarma (CDR), V. Sharma (Bank)
    registry = IdentityRegistry()
    p_id = registry.register_claim(make_claim("fir_1", "Vikram Sharma", source_record_id="src_1", national_id="SYN-NID-001", phone="+91 98450-12345"))
    
    decisions_cdr = decide_candidates(registry, make_claim("cdr_1", "Bikram Sarma", source_record_id="src_2", national_id="SYN-NID-001"))
    assert decisions_cdr[0].status is ResolutionStatus.MATCHED
    assert decisions_cdr[0].auto_link_allowed
    registry.register_claim(make_claim("cdr_1", "Bikram Sarma", source_record_id="src_2", national_id="SYN-NID-001"), person_id=p_id)
    
    decisions_bank = decide_candidates(registry, make_claim("bank_1", "V. Sharma", source_record_id="src_3", national_id="SYN-NID-001"))
    assert decisions_bank[0].status is ResolutionStatus.MATCHED
    assert decisions_bank[0].auto_link_allowed


def test_input_order_independence() -> None:
    claims = [
        make_claim("c1", "Vikram Sharma", source_record_id="s1", phone="9845012345", national_id="NID-1"),
        make_claim("c2", "Bikram Sarma", source_record_id="s2", phone="9845012345"),
        make_claim("c3", "V. Sharma", source_record_id="s3", national_id="NID-1")
    ]
    
    def resolve_order(ordered_claims):
        def claim_sort_key(c: IdentityClaim) -> tuple[int, str]:
            score = bool(c.national_id) * 3 + bool(c.phone_number) * 2 + bool(c.vehicle_number) * 2 + bool(c.address)
            return (-score, c.record_id)
            
        sorted_claims = sorted(ordered_claims, key=claim_sort_key)
        reg = IdentityRegistry()
        for c in sorted_claims:
            decs = decide_candidates(reg, c)
            auto = next((d.candidate_person_id for d in decs if d.auto_link_allowed), None)
            reg.register_claim(c, person_id=auto)
        return len(reg.profiles)
        
    assert resolve_order(claims) == 1
    assert resolve_order(list(reversed(claims))) == 1


def test_ground_truth_correctness_and_metric_bug_resolved(tmp_path: Path) -> None:
    # No self-comparison metric bug
    # Write a ground truth CSV
    gt_file = tmp_path / "entity_resolution_ground_truth.csv"
    gt_file.write_text(
        "record_a_id,record_b_id,expected_same_entity,reason\n"
        "r1,r2,True,positive match\n"
        "r1,r3,False,hard negative\n"
        "r4,r5,True,missed match (FN)\n"
        "r6,r7,False,wrong match (FP)\n",
        encoding="utf-8"
    )
    
    # We simulate a mapping that perfectly maps r1 and r2, keeps r3 separate,
    # misses r4/r5, and incorrectly maps r6/r7.
    mapping = {
        "r1": "person_1",
        "r2": "person_1",  # TP
        "r3": "person_2",  # TN (against r1)
        "r4": "person_3",
        "r5": "person_4",  # FN
        "r6": "person_5",
        "r7": "person_5",  # FP
    }
    
    metrics = evaluate_ground_truth(gt_file, mapping, [])
    assert metrics["evaluated"] is True
    assert metrics["true_positives"] == 1
    assert metrics["true_negatives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["false_positives"] == 1
    assert ("r4", "r5") in metrics["false_negative_pairs"] or ("r5", "r4") in metrics["false_negative_pairs"]
    assert ("r6", "r7") in metrics["false_positive_pairs"] or ("r7", "r6") in metrics["false_positive_pairs"]
    assert metrics["precision"] == 0.5  # TP / (TP + FP) = 1 / 2
    assert metrics["recall"] == 0.5     # TP / (TP + FN) = 1 / 2
    
