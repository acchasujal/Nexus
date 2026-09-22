"""tests/test_snapshot_resolution.py

Phase 3 Verification: Canonical Snapshot Resolution & Topology Integrity.
Verifies that:
  - Network Before & After resolve from the canonical snapshot registry.
  - Every relationship reported in diff added_relationships exists in the after snapshot.
  - Snapshot aliases resolve deterministically.
  - dataset_version travels consistently through network and diff endpoints.
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.core.graph.demo_snapshots import (
    resolve_snapshot_id,
    get_canonical_snapshot_store,
    BEFORE_NODES,
    AFTER_NODES,
    BEFORE_EDGES,
    AFTER_EDGES,
)
from backend.app.main import app
from shared.contracts.api import (
    CANONICAL_DATASET_VERSION,
    CANONICAL_SNAPSHOT_BASELINE,
    CANONICAL_SNAPSHOT_CURRENT,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_resolve_snapshot_id_aliases():
    """Verify deterministic snapshot alias resolution."""
    assert resolve_snapshot_id("before") == CANONICAL_SNAPSHOT_BASELINE
    assert resolve_snapshot_id("baseline") == CANONICAL_SNAPSHOT_BASELINE
    assert resolve_snapshot_id("SNAP-BEFORE-001") == CANONICAL_SNAPSHOT_BASELINE
    assert resolve_snapshot_id(CANONICAL_SNAPSHOT_BASELINE) == CANONICAL_SNAPSHOT_BASELINE

    assert resolve_snapshot_id("after") == CANONICAL_SNAPSHOT_CURRENT
    assert resolve_snapshot_id("current") == CANONICAL_SNAPSHOT_CURRENT
    assert resolve_snapshot_id("SNAP-AFTER-001") == CANONICAL_SNAPSHOT_CURRENT
    assert resolve_snapshot_id("SNAP-REAL") == CANONICAL_SNAPSHOT_CURRENT
    assert resolve_snapshot_id(CANONICAL_SNAPSHOT_CURRENT) == CANONICAL_SNAPSHOT_CURRENT

    # Fallback to provided ID
    assert resolve_snapshot_id("custom-snap-99") == "custom-snap-99"


def test_canonical_snapshot_stores():
    """Verify that canonical snapshot stores contain expected nodes and edges."""
    before_store = get_canonical_snapshot_store(CANONICAL_SNAPSHOT_BASELINE)
    after_store = get_canonical_snapshot_store(CANONICAL_SNAPSHOT_CURRENT)

    assert len(before_store.nodes) >= len(BEFORE_NODES)
    assert len(after_store.nodes) >= len(AFTER_NODES)

    # Rafiq alias unified node in after store
    assert "P-RAFIQ" in after_store.nodes
    # Bridge relationship exists in after store
    all_after_edge_ids = {
        props.get("id")
        for adj_list in after_store.adj.values()
        for edge in adj_list
        for props in [edge.properties]
    }
    assert "E-BRIDGE" in all_after_edge_ids


def test_api_network_and_diff_consistency(client):
    """
    Verify /nexus/network and /nexus/diff share the same snapshot registry
    and every added relationship in diff exists in after network.
    """
    # 1. Fetch Network Before
    resp_before = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_BASELINE}",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp_before.status_code == 200
    net_before = resp_before.json()
    assert net_before["snapshot_id"] == CANONICAL_SNAPSHOT_BASELINE
    assert net_before["dataset_version"] == CANONICAL_DATASET_VERSION

    # 2. Fetch Network After
    resp_after = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp_after.status_code == 200
    net_after = resp_after.json()
    assert net_after["snapshot_id"] == CANONICAL_SNAPSHOT_CURRENT
    assert net_after["dataset_version"] == CANONICAL_DATASET_VERSION

    # 3. Fetch Diff
    resp_diff = client.get(
        f"/api/v1/nexus/diff?before={CANONICAL_SNAPSHOT_BASELINE}&after={CANONICAL_SNAPSHOT_CURRENT}",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp_diff.status_code == 200
    diff_data = resp_diff.json()
    assert diff_data["dataset_version"] == CANONICAL_DATASET_VERSION
    assert diff_data["before_snapshot_id"] == CANONICAL_SNAPSHOT_BASELINE
    assert diff_data["after_snapshot_id"] == CANONICAL_SNAPSHOT_CURRENT

    # Invariant: Every added relationship in diff must exist in after snapshot
    after_edge_ids = {e["id"] for e in net_after["edges"]}
    for rel_id in diff_data["added_relationships"]:
        assert rel_id in after_edge_ids, f"Diff added relationship {rel_id} not found in after network!"

    # Invariant: Every added node in diff must exist in after snapshot
    after_node_ids = {n["id"] for n in net_after["nodes"]}
    for node_id in diff_data["added_nodes"]:
        assert node_id in after_node_ids, f"Diff added node {node_id} not found in after network!"


def test_api_network_case_scoping(client):
    """Verify that case_id parameter scopes the network graph accurately."""
    resp = client.get(
        f"/api/v1/nexus/network?snapshot={CANONICAL_SNAPSHOT_CURRENT}&case_id=CASE-141",
        headers={"X-User-Role": "ADMIN", "X-User-Id": "officer-001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] == CANONICAL_SNAPSHOT_CURRENT
    # All returned nodes should belong to CASE-141
    for node in data["nodes"]:
        assert "CASE-141" in node["case_ids"] or node["id"] == "CASE-141"
