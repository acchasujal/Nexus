"""tests/ai/test_entity_resolver.py

Comprehensive unit tests for backend.app.ai.entity_resolver.EntityResolver.
Verifies police station, district, offence category, case stage, risk band,
FIR/case identifier normalization, unknown entity passthrough, and full Intent resolution.
"""

from __future__ import annotations

import pytest

from backend.app.ai.entity_resolver import EntityResolver
from backend.app.ai.schemas import Entity, Intent


@pytest.fixture
def resolver() -> EntityResolver:
    return EntityResolver()


# ── Police Station Normalization Tests ───────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("Ashok Nagar Police Station", "Ashok Nagar"),
        ("Ashok Nagar police station", "Ashok Nagar"),
        ("Ashok Nagar PS", "Ashok Nagar"),
        ("PS Ashok Nagar", "Ashok Nagar"),
        ("Police Station Ashok Nagar", "Ashok Nagar"),
        ("Jayanagar PS", "Jayanagar"),
        ("Malleshwaram police station", "Malleshwaram"),
        ("Belagavi North Police Station", "Belagavi North"),
    ],
)
def test_normalize_police_station(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_police_station(raw_input) == expected


# ── District Normalization Tests ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("Bangalore", "Bengaluru City"),
        ("Bengaluru", "Bengaluru City"),
        ("bengaluru", "Bengaluru City"),
        ("BENGALURU", "Bengaluru City"),
        ("Belgaum", "Belagavi"),
        ("belagavi", "Belagavi"),
        ("Mysore", "Mysuru"),
        ("mysuru", "Mysuru"),
        ("Mangalore", "Mangaluru"),
        ("mangaluru", "Mangaluru"),
        ("Hubballi", "Hubballi-Dharwad"),
    ],
)
def test_normalize_district(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_district(raw_input) == expected


# ── Offence Category Normalization Tests ──────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("Vehicle Theft", "vehicle_theft"),
        ("vehicle theft", "vehicle_theft"),
        ("vehicle_theft", "vehicle_theft"),
        ("VEHICLE_THEFT", "vehicle_theft"),
        ("Cyber Fraud", "cyber_fraud"),
        ("cyber fraud", "cyber_fraud"),
        ("cyber_fraud", "cyber_fraud"),
        ("theft", "theft"),
        ("fraud", "fraud"),
        ("burglary", "burglary"),
        ("robbery", "robbery"),
        ("drug case", "narcotics"),
        ("narcotics", "narcotics"),
        ("ndps", "narcotics"),
    ],
)
def test_normalize_offence_category(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_offence_category(raw_input) == expected


# ── Case Stage Normalization Tests ────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("pending", "further_investigation"),
        ("Pending", "further_investigation"),
        ("PENDING", "further_investigation"),
        ("further investigation", "further_investigation"),
        ("further-investigation", "further_investigation"),
        ("completed", "charge_sheet_filed"),
        ("closed", "charge_sheet_filed"),
        ("chargesheet filed", "charge_sheet_filed"),
        ("charge sheet filed", "charge_sheet_filed"),
        ("charge-sheet filed", "charge_sheet_filed"),
        ("chargesheeted", "charge_sheet_filed"),
        ("investigation", "investigation"),
        ("charge sheet draft", "charge_sheet_draft"),
    ],
)
def test_normalize_case_stage(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_case_stage(raw_input) == expected


# ── Risk Band Normalization Tests ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("RED", "red"),
        ("Red", "red"),
        ("red", "red"),
        ("GREEN", "green"),
        ("Green", "green"),
        ("green", "green"),
        ("AMBER", "amber"),
        ("Amber", "amber"),
        ("OVERDUE", "overdue"),
    ],
)
def test_normalize_risk_band(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_risk_band(raw_input) == expected


# ── Identifier Normalization Tests ─────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw_input,expected",
    [
        (" fir / bel / 0064 ", "FIR/BEL/0064"),
        ("FIR/BEL/0064", "FIR/BEL/0064"),
        ("fir/ben/0102", "FIR/BEN/0102"),
        ("cc - 0043", "CC-0043"),
        ("CC-0043", "CC-0043"),
    ],
)
def test_normalize_identifier(
    resolver: EntityResolver, raw_input: str, expected: str
) -> None:
    assert resolver.normalize_identifier(raw_input) == expected


# ── Unknown Entity Passthrough Tests ──────────────────────────────────────────

def test_unknown_entity_type_passes_through(resolver: EntityResolver) -> None:
    entity = Entity(type="custom_type", value="  Some Custom Value  ")
    resolved = resolver.resolve_entity(entity)
    assert resolved.type == "custom_type"
    assert resolved.value == "Some Custom Value"


def test_unmapped_value_passes_through(resolver: EntityResolver) -> None:
    entity = Entity(type="police_station", value="Unknown Station Name")
    resolved = resolver.resolve_entity(entity)
    assert resolved.value == "Unknown Station Name"


# ── Full Intent Resolution Test ───────────────────────────────────────────────

def test_resolve_intent_normalizes_all_contained_entities(
    resolver: EntityResolver,
) -> None:
    raw_intent = Intent(
        name="SEARCH_CASES",
        confidence=0.97,
        entities=[
            Entity(type="police_station", value="Ashok Nagar Police Station"),
            Entity(type="case_stage", value="pending"),
            Entity(type="offence_category", value="Vehicle Theft"),
            Entity(type="risk_band", value="RED"),
        ],
    )

    resolved = resolver.resolve(raw_intent)

    assert resolved.name == "SEARCH_CASES"
    assert resolved.confidence == 0.97
    assert len(resolved.entities) == 4

    assert resolved.entities[0].type == "police_station"
    assert resolved.entities[0].value == "Ashok Nagar"

    assert resolved.entities[1].type == "case_stage"
    assert resolved.entities[1].value == "further_investigation"

    assert resolved.entities[2].type == "offence_category"
    assert resolved.entities[2].value == "vehicle_theft"

    assert resolved.entities[3].type == "risk_band"
    assert resolved.entities[3].value == "red"
