"""tests/graph/test_graph_schema_v2.py

Comprehensive tests for NEXUS Graph Schema V2 contract:
  - Required entity validation (Person, Phone, Vehicle, Account, Organization, Event, SourceRecord)
  - Canonical Node contract (id, entity_type, canonical_label, aliases, attributes, confidence)
  - Relationship contract (id, source_id, target_id, type, start_time, end_time, confidence, derivation_class, source_record_id)
  - DerivationClass taxonomy (FACT, DERIVED, HYPOTHESIS)
  - SourceRecord provenance lineage
  - M2 (Vikram) Handoff Contract Fixture verification (JSON serialization/deserialization)
"""

import json
from datetime import datetime, timezone

import pytest

from backend.app.core.graph.edges import (
    GraphEdge,
    Relationship,
)
from backend.app.core.graph.entities import (
    Account,
    Event,
    GraphEntityBase,
    Node,
    Organization,
    Person,
    Phone,
    SourceRecord,
    Vehicle,
)
from backend.app.core.graph.enums import (
    DerivationClass,
    GraphEntityType,
    GraphRelationshipType,
)
from backend.app.core.graph.graph_schema import GRAPH_SCHEMA

# ── Node Contract Tests ─────────────────────────────────────────────────────────

def test_person_node_validates():
    person = Person(
        id="person_001",
        full_name="Rahul Kumar",
        aliases=["R. Kumar", "Bhai"],
        phone_numbers=["9876543210"],
        confidence=1.0,
    )
    assert person.id == "person_001"
    assert person.entity_type == GraphEntityType.PERSON
    assert person.canonical_label == "Rahul Kumar"
    assert "R. Kumar" in person.aliases
    assert person.confidence == 1.0
    assert person.attributes["full_name"] == "Rahul Kumar"


def test_phone_node_validates():
    phone = Phone(
        id="phone_001",
        phone_number="9876543210",
        imei="864201041234567",
        confidence=0.95,
    )
    assert phone.id == "phone_001"
    assert phone.entity_type == GraphEntityType.PHONE
    assert phone.canonical_label == "9876543210"
    assert phone.confidence == 0.95


def test_account_node_validates():
    account = Account(
        id="account_001",
        account_number="ACC99887766",
        bank_name="State Bank of India",
        ifsc_code="SBIN0001234",
        confidence=1.0,
    )
    assert account.id == "account_001"
    assert account.entity_type == GraphEntityType.ACCOUNT
    assert account.canonical_label == "ACC99887766"


def test_source_record_validates():
    sr = SourceRecord(
        id="src_rec_101",
        batch_id="batch_2026_08_24",
        source_type="CDR",
        locator="cdr_dump_bengaluru.csv:line_42",
        raw_excerpt="9876543210,9123456789,2026-08-24T14:30:00Z,300",
        content_hash="a1b2c3d4e5f67890123456789abcdef0",
        hash_algorithm="SHA-256",
        confidence=1.0,
    )
    assert sr.id == "src_rec_101"
    assert sr.entity_type == GraphEntityType.SOURCE_RECORD
    assert sr.batch_id == "batch_2026_08_24"
    assert sr.locator == "cdr_dump_bengaluru.csv:line_42"
    assert sr.content_hash == "a1b2c3d4e5f67890123456789abcdef0"
    assert sr.hash_algorithm == "SHA-256"


def test_generic_node_contract():
    node = Node(
        id="node_custom_1",
        entity_type=GraphEntityType.VEHICLE,
        canonical_label="KA-01-AB-1234",
        aliases=["White Swift"],
        attributes={"color": "White", "make": "Maruti"},
        confidence=0.85,
    )
    assert node.id == "node_custom_1"
    assert node.entity_type == GraphEntityType.VEHICLE
    assert node.canonical_label == "KA-01-AB-1234"
    assert node.aliases == ["White Swift"]
    assert node.attributes["color"] == "White"
    assert node.confidence == 0.85


def test_node_id_validation_fails_on_empty():
    with pytest.raises(ValueError, match="Node id must be a non-empty string"):
        Person(id="")

    with pytest.raises(ValueError, match="Node id must be a non-empty string"):
        GraphEntityBase(id="   ")


def test_node_confidence_validation_fails_out_of_range():
    with pytest.raises((ValueError, Exception)):
        Person(id="p1", confidence=1.5)

    with pytest.raises((ValueError, Exception)):
        Phone(id="ph1", confidence=-0.1)


# ── Relationship Contract Tests ────────────────────────────────────────────────

def test_communication_relationship_validates():
    t_start = datetime(2026, 8, 24, 14, 30, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 8, 24, 14, 35, 0, tzinfo=timezone.utc)
    rel = Relationship(
        id="rel_comm_01",
        source_id="phone_001",
        target_id="phone_002",
        type=GraphRelationshipType.COMMUNICATED_WITH,
        start_time=t_start,
        end_time=t_end,
        confidence=1.0,
        derivation_class=DerivationClass.FACT,
        source_record_id="src_rec_101",
    )
    assert rel.id == "rel_comm_01"
    assert rel.source_id == "phone_001"
    assert rel.target_id == "phone_002"
    assert rel.type == GraphRelationshipType.COMMUNICATED_WITH
    assert rel.start_time == t_start
    assert rel.end_time == t_end
    assert rel.confidence == 1.0
    assert rel.derivation_class == DerivationClass.FACT
    assert rel.source_record_id == "src_rec_101"
    assert rel.provenance.source_record_id == "src_rec_101"


def test_financial_relationship_validates():
    t_txn = datetime(2026, 8, 24, 15, 0, 0, tzinfo=timezone.utc)
    rel = GraphEdge(
        source_id="account_001",
        target_id="account_002",
        edge_type=GraphRelationshipType.TRANSFERRED_FUNDS,
        start_time=t_txn,
        confidence=0.9,
        derivation_class=DerivationClass.FACT,
        properties={"amount": 500000.0, "utr": "UTR998877"},
    )
    assert rel.id == "rel_account_001_TRANSFERRED_FUNDS_account_002"
    assert rel.type == GraphRelationshipType.TRANSFERRED_FUNDS
    assert rel.confidence == 0.9
    assert rel.properties["amount"] == 500000.0


def test_derived_and_hypothesis_relationships():
    rel_derived = GraphEdge(
        source_id="person_001",
        target_id="person_002",
        edge_type=GraphRelationshipType.CO_ACCUSED_WITH,
        confidence=0.85,
        derivation_class=DerivationClass.DERIVED,
    )
    assert rel_derived.derivation_class == DerivationClass.DERIVED

    rel_hypothesis = GraphEdge(
        source_id="person_001",
        target_id="org_001",
        edge_type=GraphRelationshipType.ASSOCIATED_WITH,
        confidence=0.5,
        derivation_class=DerivationClass.HYPOTHESIS,
    )
    assert rel_hypothesis.derivation_class == DerivationClass.HYPOTHESIS


def test_relationship_invalid_node_ids_fail():
    with pytest.raises((ValueError, Exception)):
        GraphEdge(source_id="", target_id="p2", edge_type=GraphRelationshipType.CONNECTED_TO)

    with pytest.raises((ValueError, Exception)):
        GraphEdge(source_id="p1", target_id="  ", edge_type=GraphRelationshipType.CONNECTED_TO)


def test_relationship_invalid_confidence_fails():
    with pytest.raises((ValueError, Exception)):
        GraphEdge(source_id="p1", target_id="p2", edge_type=GraphRelationshipType.CONNECTED_TO, confidence=1.2)


def test_relationship_invalid_temporal_window_fails():
    t_start = datetime(2026, 8, 24, 15, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 8, 24, 14, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="start_time .* cannot be later than end_time"):
        GraphEdge(
            source_id="p1",
            target_id="p2",
            edge_type=GraphRelationshipType.CONNECTED_TO,
            start_time=t_start,
            end_time=t_end,
        )


# ── M2 Handoff Contract & Serialization Test ───────────────────────────────────

def test_m2_handoff_contract_fixture_serialization():
    """
    Demonstrates that Vikram (M2) can construct, serialize, and deserialize all canonical
    V2 graph objects (Person, Phone, Vehicle, Account, Organization, Event, SourceRecord, Relationship)
    using ONLY the V2 contract without inventing custom fields or coercing types.
    """
    # 1. SourceRecord
    src_rec = SourceRecord(
        id="src_rec_001",
        batch_id="batch_sih_001",
        source_type="CDR",
        locator="telecom_log_01.csv:102",
        raw_excerpt="9876543210 -> 9123456789 at 14:32",
        hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        occurred_at=datetime(2026, 8, 24, 14, 32, 0, tzinfo=timezone.utc),
    )

    # 2. V2 Entities
    person = Person(
        id="person_001",
        full_name="Vikram Sharma",
        aliases=["Vicky", "Doctor"],
        phone_numbers=["9876543210"],
        vehicles=["KA-01-MJ-9999"],
        national_id="ID-998877",
        confidence=1.0,
    )

    phone = Phone(
        id="phone_001",
        phone_number="9876543210",
        imei="864201041234567",
        carrier="Airtel",
        confidence=1.0,
    )

    vehicle = Vehicle(
        id="vehicle_001",
        registration_number="KA-01-MJ-9999",
        vehicle_type="SUV",
        make="Mahindra",
        model="Thar",
        color="Black",
        confidence=1.0,
    )

    account = Account(
        id="account_001",
        account_number="ACC-100200300",
        bank_name="HDFC Bank",
        ifsc_code="HDFC0000123",
        confidence=1.0,
    )

    org = Organization(
        id="org_001",
        name="Apex Trading Syndicate",
        org_type="Front Company",
        jurisdiction="Bengaluru",
        confidence=0.9,
    )

    event = Event(
        id="event_001",
        event_type="MEETING",
        description="Planning meeting at Indiranagar cafe",
        timestamp=datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc),
        participant_ids=["person_001"],
        confidence=0.95,
    )

    # 3. V2 Relationships
    rel_phone = Relationship(
        id="rel_001",
        source_id=person.id,
        target_id=phone.id,
        type=GraphRelationshipType.USED_PHONE,
        confidence=1.0,
        derivation_class=DerivationClass.FACT,
        source_record_id=src_rec.id,
    )

    rel_comm = Relationship(
        id="rel_002",
        source_id=phone.id,
        target_id="phone_002",
        type=GraphRelationshipType.COMMUNICATED_WITH,
        start_time=datetime(2026, 8, 24, 14, 32, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 24, 14, 37, 0, tzinfo=timezone.utc),
        confidence=1.0,
        derivation_class=DerivationClass.FACT,
        source_record_id=src_rec.id,
    )

    # Verify JSON serialization round-trip for all V2 objects
    graph_bundle = {
        "nodes": [
            src_rec.model_dump(mode="json"),
            person.model_dump(mode="json"),
            phone.model_dump(mode="json"),
            vehicle.model_dump(mode="json"),
            account.model_dump(mode="json"),
            org.model_dump(mode="json"),
            event.model_dump(mode="json"),
        ],
        "relationships": [
            rel_phone.model_dump(mode="json"),
            rel_comm.model_dump(mode="json"),
        ],
    }

    serialized_json = json.dumps(graph_bundle)
    assert len(serialized_json) > 0

    deserialized = json.loads(serialized_json)
    assert len(deserialized["nodes"]) == 7
    assert len(deserialized["relationships"]) == 2

    # Verify entity deserialization back to Pydantic models
    recreated_person = Person.model_validate(deserialized["nodes"][1])
    assert recreated_person.id == "person_001"
    assert recreated_person.canonical_label == "Vikram Sharma"
    assert "Doctor" in recreated_person.aliases

    recreated_rel = Relationship.model_validate(deserialized["relationships"][1])
    assert recreated_rel.type == GraphRelationshipType.COMMUNICATED_WITH
    assert recreated_rel.derivation_class == DerivationClass.FACT
    assert recreated_rel.source_record_id == "src_rec_001"


def test_graph_schema_definition():
    assert GraphEntityType.SOURCE_RECORD in GRAPH_SCHEMA.entities
    assert GraphRelationshipType.COMMUNICATED_WITH in GRAPH_SCHEMA.relationships
    assert GraphRelationshipType.TRANSFERRED_FUNDS in GRAPH_SCHEMA.relationships
