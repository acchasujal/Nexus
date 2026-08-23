"""
tests/graph/test_entity_resolution.py

Tests for Entity Resolution (ER) module.
Covers exact matching, case-insensitivity, spacing, punctuation, slight spelling mistakes,
phonetic spelling variations, multiple match candidate ranking, low confidence filtering,
and address boosts. Also covers the resolved pattern detection integration.
"""

from backend.app.core.graph.algorithms.entity_resolution import (
    normalize_text,
    phonetic_normalize,
    jaccard_similarity,
    resolve_person,
)
from backend.app.core.graph.algorithms.pattern_detection import (
    detect_repeat_accused_resolved,
)
from helpers import _FakeNode, _FakeEdge, make_store


def test_normalization():
    # Lowercase & spacing & punctuation
    assert normalize_text("Amit   SHARMA!!!") == "amit sharma"
    assert normalize_text("O'Connor") == "oconnor"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_phonetic_normalization():
    # Common sound-alikes mapped to a canonical form
    assert phonetic_normalize("Sharma") == phonetic_normalize("Sarma")
    assert phonetic_normalize("Reddy") == phonetic_normalize("Reddi")
    assert phonetic_normalize("Gowda") == phonetic_normalize("Gauda")
    assert phonetic_normalize("Singhal") == phonetic_normalize("Sinhal")
    #Swamy / Swami / Svamy
    assert phonetic_normalize("Swamy") == phonetic_normalize("Swami")
    assert phonetic_normalize("Swamy") == phonetic_normalize("Svamy")


def test_jaccard_similarity():
    assert jaccard_similarity("sarma", "sarma") == 1.0
    assert jaccard_similarity("sarma", "sharma") == 0.5  # bigram overlap (ar, rm, ma vs sh, ha, ar, rm, ma)
    assert jaccard_similarity("amit", "sumit") == 0.4


def test_entity_resolution_exact_and_fuzzy():
    # Create mock person nodes
    p1 = _FakeNode("Person", {
        "full_name": "Amit Sharma",
        "phone_number": "+91-9876543210",
        "address_text": "123, MG Road, Bengaluru",
        "aliases": ["Sunny"]
    })
    
    p2 = _FakeNode("Person", {
        "full_name": "Reddy S.",
        "phone_number": "+91-9988776655",
        "address_text": "456, Residency Rd, Bengaluru",
        "aliases": []
    })
    
    store = make_store([p1, p2], [])
    
    # 1. Exact Name match
    matches = resolve_person(store, {"full_name": "Amit Sharma"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0  # Exact match (std similarity of bigrams)
    assert "full_name" in matches[0].matched_fields
    
    # 2. Case Insensitive / Spacing Match
    matches = resolve_person(store, {"full_name": "  amit    sharma  "})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0

    # 3. Phone number match (extremely high confidence)
    matches = resolve_person(store, {"phone_number": "9876543210"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0
    assert "phone_number" in matches[0].matched_fields

    # 4. Phonetic name match (sharma vs sarma)
    matches = resolve_person(store, {"full_name": "Amit Sarma"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0  # Phonetic normalize maps both to "amit sarma"

    # 5. Punctuation removal
    matches = resolve_person(store, {"full_name": "Amit Sharma!!!"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0


def test_entity_resolution_alias_and_address_boost():
    p1 = _FakeNode("Person", {
        "full_name": "Vikram Gowda",
        "phone_number": "+91-9888888888",
        "address_text": "Sector 5, HSR Layout, Bengaluru",
        "aliases": ["Vicky", "Viku"]
    })
    store = make_store([p1], [])

    # Match by alias (standard)
    matches = resolve_person(store, {"full_name": "Vicky"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence == 1.0
    assert "aliases" in matches[0].matched_fields

    # Match by alias (phonetic/fuzzy)
    matches = resolve_person(store, {"full_name": "Vicki"})
    assert len(matches) > 0
    assert matches[0].matched_node_id == p1.id
    assert matches[0].confidence >= 0.70

    # Address boost test
    # Without address match
    matches_no_addr = resolve_person(store, {"full_name": "Vikram Gowde"})
    assert len(matches_no_addr) > 0
    score_no_addr = matches_no_addr[0].confidence
    
    # With highly similar address
    matches_addr = resolve_person(store, {
        "full_name": "Vikram Gowde",
        "address_text": "Sector 5, HSR Layout, Bangalore"
    })
    assert len(matches_addr) > 0
    score_addr = matches_addr[0].confidence
    assert score_addr > score_no_addr
    assert "address_text" in matches_addr[0].matched_fields


def test_multiple_possible_matches_and_low_confidence():
    p1 = _FakeNode("Person", {"full_name": "Rajesh Kumar"})
    p2 = _FakeNode("Person", {"full_name": "Rajesh Sharma"})
    p3 = _FakeNode("Person", {"full_name": "Rakesh Kumar"})
    store = make_store([p1, p2, p3], [])

    # Rajesh should return both Rajesh Kumar and Rajesh Sharma, ranked
    matches = resolve_person(store, {"full_name": "Rajesh"})
    assert len(matches) >= 2
    # Ensure they are sorted by confidence descending
    assert matches[0].confidence >= matches[1].confidence
    
    # Low confidence query should return candidates, but they'll be below automatic cutoff
    matches_low = resolve_person(store, {"full_name": "Rajes"})
    # "Rajes" matches Rajesh Kumar with moderate similarity
    assert len(matches_low) > 0
    assert matches_low[0].confidence < 0.70  # Low confidence refusal threshold


def test_resolved_repeat_accused_pattern():
    p1 = _FakeNode("Person", {"full_name": "Amit Sharma", "role": "accused"})
    p2 = _FakeNode("Person", {"full_name": "Amit Sarma", "role": "accused"})
    p3 = _FakeNode("Person", {"full_name": "Rohan Das", "role": "accused"})
    
    c1 = _FakeNode("Case", {"fir_number": "FIR/01"})
    c2 = _FakeNode("Case", {"fir_number": "FIR/02"})
    c3 = _FakeNode("Case", {"fir_number": "FIR/03"})
    
    # Edges:
    # p1 (Amit Sharma) is accused in c1
    # p2 (Amit Sarma) is accused in c2
    # p3 (Rohan Das) is accused in c3
    e1 = _FakeEdge("ACCUSED_IN", p1.id, c1.id)
    e2 = _FakeEdge("ACCUSED_IN", p2.id, c2.id)
    e3 = _FakeEdge("ACCUSED_IN", p3.id, c3.id)
    
    store = make_store([p1, p2, p3, c1, c2, c3], [e1, e2, e3])
    
    # Normal repeat accused detection (needs exact Person node reuse)
    repeats_normal = [e for e in store.adj.keys() if len(store.adj[e]) >= 2] # none
    assert len(repeats_normal) == 0
    
    # Resolved repeat accused clustering (groups Amit Sharma + Amit Sarma)
    repeats_resolved = detect_repeat_accused_resolved(store, min_cases=2, confidence_threshold=0.70)
    assert len(repeats_resolved) == 1
    assert repeats_resolved[0].canonical_person_name == "Amit Sharma"
    assert len(repeats_resolved[0].person_ids) == 2
    assert len(repeats_resolved[0].case_ids) == 2
    assert repeats_resolved[0].case_count == 2
