from typing import Any
from uuid import uuid4

from backend.app.core.graph.algorithms.utils import (
    GraphStore,
    build_graph_store,
)

class _FakeNode:
    """Minimal stand-in for SyntheticNodeRecord."""

    def __init__(self, entity_type: str, properties: dict[str, Any] | None = None) -> None:
        self.id = str(uuid4())
        # build_graph_store reads entity_type.value if it has .value, else str()
        self.entity_type = _FakeEnum(entity_type)
        self.properties = properties or {}


class _FakeEnum:
    """Mimics an Enum with a .value attribute."""

    def __init__(self, value: str) -> None:
        self.value = value


class _FakeEdge:
    """Minimal stand-in for SyntheticEdgeRecord."""

    def __init__(self, edge_type: str, source_id: str, target_id: str, **props: Any) -> None:
        self.edge_type = _FakeEnum(edge_type)
        self.source_id = source_id
        self.target_id = target_id
        self.properties = props










def make_case(district: str = "Bengaluru City", station: str = "Ashok Nagar",
              offence_category: str = "theft", risk_band: str = "green",
              case_stage: str = "investigation", crime_head_id: str | None = None,
              crime_sub_head_id: str | None = None,
              reported_at: str | None = None) -> _FakeNode:
    props: dict[str, Any] = {
        "district": district,
        "police_station": station,
        "offence_category": offence_category,
        "risk_band": risk_band,
        "case_stage": case_stage,
        "fir_number": f"FIR/{district[:3].upper()}/0001",
    }
    if reported_at:
        props["reported_at"] = reported_at
    return _FakeNode("Case", props)


def make_person(role: str = "accused", district: str = "Bengaluru City",
                phone_cluster: str | None = None, vehicle_cluster: str | None = None,
                address_cluster: str | None = None) -> _FakeNode:
    return _FakeNode("Person", {
        "role": role,
        "district": district,
        "shared_phone_cluster_id": phone_cluster or "",
        "shared_vehicle_cluster_id": vehicle_cluster or "",
        "shared_address_cluster_id": address_cluster or "",
    })


def make_officer(badge: str = "KA-0001", district: str = "Bengaluru City",
                 rank: str = "inspector") -> _FakeNode:
    return _FakeNode("Officer", {
        "badge_number": badge,
        "full_name": f"Officer {badge}",
        "district": district,
        "rank": rank,
    })


def make_dependency(status: str = "pending") -> _FakeNode:
    return _FakeNode("Dependency", {"status": status, "dependency_type": "FSL report"})


def make_clock(status: str = "green", days_remaining: int = 30) -> _FakeNode:
    return _FakeNode("ClockInstance", {
        "status": status,
        "days_remaining": days_remaining,
        "clock_type": "investigation_60_day",
    })


def make_evidence() -> _FakeNode:
    return _FakeNode("Evidence", {"evidence_type": "physical"})


def make_crime_head(head_name: str = "Property") -> _FakeNode:
    return _FakeNode("CrimeHead", {"head_name": head_name, "head_code": "CH-01"})


def make_crime_sub_head(sub_name: str = "Theft") -> _FakeNode:
    return _FakeNode("CrimeSubHead", {"sub_head_name": sub_name})


def make_section(code: str = "SECTION_THEFT") -> _FakeNode:
    return _FakeNode("Section", {"section_code": code})


def make_store(nodes: list[_FakeNode], edges: list[_FakeEdge]) -> GraphStore:
    return build_graph_store(nodes, edges)
