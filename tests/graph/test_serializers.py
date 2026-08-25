from dataclasses import dataclass
from datetime import datetime

from backend.app.core.graph.algorithms.utils import AdjEdge, NodeRecord
from backend.app.core.graph.services.serializers import (
    serialize_dataclass,
    serialize_edge,
    serialize_node,
)


class Dummy:
    def __init__(self):
        self.x = 1





@dataclass
class Sample:
    number: int
    created: datetime
    tags: set[str]


def test_serialize_node():
    node = NodeRecord(
        node_id="case-1",
        entity_type="Case",
        properties={"district": "Bengaluru"},
    )

    result = serialize_node(node)

    assert result["node_id"] == "case-1"
    assert result["entity_type"] == "Case"
    assert result["properties"]["district"] == "Bengaluru"


def test_serialize_none_node():
    assert serialize_node(None) is None


def test_serialize_edge():
    edge = AdjEdge(
        source_id="p1",
        target_id="c1",
        edge_type="ACCUSED_IN",
        properties={"role": "primary"},
    )

    result = serialize_edge(edge)

    assert result["source_id"] == "p1"
    assert result["target_id"] == "c1"
    assert result["edge_type"] == "ACCUSED_IN"


def test_serialize_dataclass():
    sample = Sample(
        number=5,
        created=datetime(2026, 1, 1),
        tags={"A", "B"},
    )

    result = serialize_dataclass(sample)

    assert result["number"] == 5
    assert isinstance(result["created"], str)
    assert sorted(result["tags"]) == ["A", "B"]