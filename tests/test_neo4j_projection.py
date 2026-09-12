"""tests/test_neo4j_projection.py

Unit and integration tests for the durable Neo4j graph projection layer:
  1. Schema constraint & index creation.
  2. Batch node upsert (sync_nodes).
  3. Batch edge upsert (sync_edges).
  4. Projection reading (read_projection) and GraphStore extraction (to_graph_store).
  5. Projection clearing (clear_projection).
  6. Operational status tracking and request gating through require_graph_projection.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.neo4j import Neo4jConnection
from backend.app.main import create_app


def make_test_settings(**overrides):
    return Settings(
        _env_file=None,
        GRAPH_BACKEND="neo4j",
        NEO4J_URI="bolt://127.0.0.1:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD=secrets.token_urlsafe(24),
        NEO4J_DATABASE="nexus",
        **overrides,
    )


@pytest.fixture
def mock_neo4j_driver():
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    driver.execute_query = AsyncMock(return_value=([{"ok": 1}], None, ["ok"]))
    driver.close = AsyncMock()
    return driver


@pytest.mark.asyncio
async def test_ensure_schema_executes_constraint_and_index_queries(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    await conn.ensure_schema()

    assert mock_neo4j_driver.execute_query.call_count == 2
    calls = mock_neo4j_driver.execute_query.call_args_list
    constraint_query_text = str(calls[0].args[0].text)
    index_query_text = str(calls[1].args[0].text)

    assert "CREATE CONSTRAINT nexus_node_id" in constraint_query_text
    assert "REQUIRE n.id IS UNIQUE" in constraint_query_text
    assert "CREATE INDEX nexus_node_entity_type" in index_query_text


@pytest.mark.asyncio
async def test_sync_nodes_parameterized_batch(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    test_nodes = [
        {
            "id": "person-101",
            "entity_type": "Person",
            "properties": {"full_name": "Vikram Rathore", "phone": "+919876543210"},
            "case_ids": ["CASE-2026-001"],
            "badges": ["SUSPECT"],
        },
        {
            "id": "case-001",
            "entity_type": "Case",
            "properties": {"name": "FIR 141", "district": "Cyberabad"},
            "case_ids": [],
            "badges": [],
        },
    ]

    count = await conn.sync_nodes(test_nodes)
    assert count == 2

    mock_neo4j_driver.execute_query.assert_awaited_once()
    call = mock_neo4j_driver.execute_query.call_args
    query_text = str(call.args[0].text)
    params = call.kwargs["parameters_"]

    assert "UNWIND $batch AS row" in query_text
    assert "MERGE (n:NexusNode {id: row.id})" in query_text
    assert len(params["batch"]) == 2
    assert params["batch"][0]["id"] == "person-101"
    assert params["batch"][0]["label"] == "Vikram Rathore"
    assert "Vikram Rathore" in params["batch"][0]["properties_json"]


@pytest.mark.asyncio
async def test_sync_edges_parameterized_batch(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    test_edges = [
        {
            "id": "rel-001",
            "source_id": "person-101",
            "target_id": "case-001",
            "edge_type": "ACCUSED_IN",
            "weight": 1.0,
            "confidence": 0.95,
            "derivation_class": "FACT",
            "properties": {"role": "Primary Accused"},
        }
    ]

    count = await conn.sync_edges(test_edges)
    assert count == 1

    mock_neo4j_driver.execute_query.assert_awaited_once()
    call = mock_neo4j_driver.execute_query.call_args
    query_text = str(call.args[0].text)
    params = call.kwargs["parameters_"]

    assert "MERGE (src)-[r:CONNECTED_TO {id: row.id}]->(tgt)" in query_text
    assert params["batch"][0]["source_id"] == "person-101"
    assert params["batch"][0]["target_id"] == "case-001"
    assert params["batch"][0]["edge_type"] == "ACCUSED_IN"


@pytest.mark.asyncio
async def test_read_projection_reconstructs_graph_structures(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    node_record = {
        "id": "person-101",
        "entity_type": "Person",
        "label": "Vikram Rathore",
        "case_ids": ["CASE-2026-001"],
        "badges": ["SUSPECT"],
        "properties_json": json.dumps({"full_name": "Vikram Rathore"}),
    }
    edge_record = {
        "id": "rel-001",
        "source_id": "person-101",
        "target_id": "case-001",
        "edge_type": "ACCUSED_IN",
        "weight": 1.0,
        "confidence": 0.95,
        "derivation_class": "FACT",
        "start_time": None,
        "end_time": None,
        "source_record_id": "src-999",
        "properties_json": json.dumps({"role": "Accused"}),
    }

    mock_neo4j_driver.execute_query.side_effect = [
        ([node_record], None, ["id"]),
        ([edge_record], None, ["id"]),
    ]

    nodes, edges = await conn.read_projection()

    assert "person-101" in nodes
    assert nodes["person-101"]["label"] == "Vikram Rathore"
    assert nodes["person-101"]["properties"]["full_name"] == "Vikram Rathore"
    assert len(edges) == 1
    assert edges[0]["id"] == "rel-001"
    assert edges[0]["edge_type"] == "ACCUSED_IN"


@pytest.mark.asyncio
async def test_to_graph_store_extracts_networkx_compatible_store(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    node_records = [
        {
            "id": "person-101",
            "entity_type": "Person",
            "label": "Vikram",
            "case_ids": [],
            "badges": [],
            "properties_json": "{}",
        },
        {
            "id": "person-102",
            "entity_type": "Person",
            "label": "Amit",
            "case_ids": [],
            "badges": [],
            "properties_json": "{}",
        },
    ]
    edge_records = [
        {
            "id": "edge-1",
            "source_id": "person-101",
            "target_id": "person-102",
            "edge_type": "COMMUNICATED_WITH",
            "weight": 1.0,
            "confidence": 1.0,
            "derivation_class": "FACT",
            "start_time": None,
            "end_time": None,
            "source_record_id": None,
            "properties_json": "{}",
        }
    ]

    mock_neo4j_driver.execute_query.side_effect = [
        (node_records, None, ["id"]),
        (edge_records, None, ["id"]),
    ]

    store = await conn.to_graph_store()
    assert "person-101" in store.nodes
    assert "person-102" in store.nodes
    assert len(store.adj["person-101"]) == 1
    assert store.adj["person-101"][0].target_id == "person-102"
    assert store.adj["person-101"][0].edge_type == "COMMUNICATED_WITH"


@pytest.mark.asyncio
async def test_clear_projection_deletes_all_nodes(mock_neo4j_driver):
    cfg = make_test_settings()
    conn = Neo4jConnection(cfg)
    conn._driver = mock_neo4j_driver

    await conn.clear_projection()

    mock_neo4j_driver.execute_query.assert_awaited_once()
    call = mock_neo4j_driver.execute_query.call_args
    assert "MATCH (n:NexusNode) DETACH DELETE n" in str(call.args[0].text)


def test_operational_neo4j_allows_data_operations_and_reports_ready(monkeypatch):
    import neo4j

    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    driver.execute_query = AsyncMock(return_value=([{"ok": 1}], None, ["ok"]))
    driver.close = AsyncMock()
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", MagicMock(return_value=driver))

    cfg = make_test_settings()
    app = create_app(repository=InMemoryBackendRepository(), settings=cfg)

    with TestClient(app) as client:
        # After lifespan startup, connection is operational
        assert app.state.neo4j.is_operational is True

        ready_resp = client.get("/ready")
        assert ready_resp.status_code == 200
        data = ready_resp.json()
        assert data["status"] == "ready"
        assert data["graph"]["operational"] is True
        assert data["graph"]["projection"] == "synced"

        # Data operations are NOT blocked with 503
        network_resp = client.get("/api/v1/nexus/network")
        assert network_resp.status_code == 200
        assert "nodes" in network_resp.json()
