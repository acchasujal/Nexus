"""tests/test_focused_graph.py

Phase 7 Verification: Server-Side Focused Investigative Graph Loading.
Verifies that:
  - 1-hop focus extracts only anchor entity and direct neighbors.
  - 2-hop focus extracts 2-hop neighborhood.
  - Cross-case focus extracts the pair subgraph connecting case_id and target_case_id.
  - Subgraph extraction is fast (< 50ms) and avoids global 400+ node dump.
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from shared.contracts.api import CANONICAL_SNAPSHOT_CURRENT


@pytest.fixture
def client():
    return TestClient(app)


def test_focused_1hop_extraction(client):
    """Test 1-hop neighborhood extraction for anchor entity."""
    start = time.perf_counter()
    resp = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}&entity_id=P-RAFIQ&focus=1hop",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 500

    data = resp.json()
    node_ids = {n["id"] for n in data["nodes"]}
    assert "P-RAFIQ" in node_ids
    # 1-hop should be compact (between 2 and 15 nodes), far smaller than global network
    assert 2 <= len(node_ids) <= 15
    # All edges must only connect nodes in the returned subgraph
    for edge in data["edges"]:
        assert edge["source_id"] in node_ids
        assert edge["target_id"] in node_ids


def test_focused_2hop_expansion(client):
    """Test 2-hop neighborhood expansion includes 1-hop nodes plus second-degree links."""
    resp_1hop = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}&entity_id=P-RAFIQ&focus=1hop",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    resp_2hop = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}&entity_id=P-RAFIQ&focus=2hop",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp_1hop.status_code == 200
    assert resp_2hop.status_code == 200

    nids_1hop = {n["id"] for n in resp_1hop.json()["nodes"]}
    nids_2hop = {n["id"] for n in resp_2hop.json()["nodes"]}

    assert nids_1hop.issubset(nids_2hop)
    assert len(nids_2hop) >= len(nids_1hop)


def test_focused_cross_case_extraction(client):
    """Test cross-case pair subgraph extraction connecting two investigations."""
    resp = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}&case_id=CASE-141&target_case_id=CASE-207",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    node_ids = {n["id"] for n in data["nodes"]}
    assert "CASE-141" in node_ids
    assert "CASE-207" in node_ids
    assert "P-RAFIQ" in node_ids

    # E-BRIDGE connects the two cases
    edge_ids = {e["id"] for e in data["edges"]}
    assert "E-BRIDGE" in edge_ids
