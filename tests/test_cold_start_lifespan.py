"""Canonical reads and login must work while the required graph is initializing."""
import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.neo4j import Neo4jConnection
from backend.app.main import create_app


def make_app():
    cfg = Settings(_env_file=None, GRAPH_BACKEND="neo4j", NEO4J_URI="bolt://localhost:7687",
                   NEO4J_USER="test", NEO4J_PASSWORD="synthetic-test-only",
                   NEO4J_BACKGROUND_STARTUP=True)
    return create_app(repository=InMemoryBackendRepository(), settings=cfg)


def test_http_serves_while_graph_is_starting_and_shutdown_cancels(monkeypatch):
    cancelled = []

    async def slow_start(self):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    monkeypatch.setattr(Neo4jConnection, "start", slow_start)
    app = make_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        login = client.post("/api/v1/auth/login", json={"username": "KA-1002", "password": "nexus-demo-passcode", "role": "SHO"})
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        bootstrap = client.get("/api/v1/nexus/intelligence/bootstrap", headers=headers)
        assert bootstrap.status_code == 200
        assert bootstrap.json()["kpis"]["active_pulses_count"] > 0
        assert client.get("/api/v1/graph/stats", headers=headers).status_code == 503
        assert client.post("/api/v1/nexus/demo/reset", headers=headers).status_code == 503
        ready = client.get("/ready")
        assert ready.status_code == 503
        assert ready.json()["startup"]["factory_to_http_ready_ms"] >= 0
        assert ready.json()["graph_initialization"]["status"] == "starting"
    assert cancelled == [True]


@pytest.mark.parametrize("fail", [False, True])
def test_background_projection_publication_and_failure(monkeypatch, fail):
    async def start(self):
        self.status = "connected"

    async def sync(self, nodes, edges):
        self.is_operational = True

    async def read(self):
        assert not self.is_operational
        if fail:
            raise RuntimeError("test read failure")
        return InMemoryBackendRepository().to_graph_store()

    monkeypatch.setattr(Neo4jConnection, "start", start)
    monkeypatch.setattr(Neo4jConnection, "ensure_schema", AsyncMock())
    monkeypatch.setattr(Neo4jConnection, "sync_projection", sync)
    monkeypatch.setattr(Neo4jConnection, "to_graph_store", read)
    app = make_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.neo4j.is_operational is (not fail)
        state = app.state.graph_initialization
        assert state["status"] == ("failed" if fail else "ready")
        assert state["stage"] == ("read" if fail else "complete")
        if fail:
            assert state["failure_type"] == "RuntimeError"
        assert client.get("/api/v1/graph/stats").status_code == (503 if fail else 200)
        assert client.get("/api/v1/nexus/intelligence/bootstrap").status_code == 200


def test_identical_fresh_sessions_have_identical_metrics_and_reads_do_not_mutate_them():
    metrics = []
    for _ in range(2):
        app = create_app(repository=InMemoryBackendRepository(), settings=Settings(_env_file=None))
        with TestClient(app) as client:
            first = client.get("/api/v1/nexus/intelligence/bootstrap").json()["kpis"]
            pulses = client.get("/api/v1/nexus/pulses").json()
            second = client.get("/api/v1/nexus/intelligence/bootstrap").json()["kpis"]
            assert first == second
            assert first["active_pulses_count"] == len(pulses)
            assert first["total_claims"] == sum(len(p["assessment"]) for p in pulses)
            metrics.append(first)
    assert metrics[0] == metrics[1]


@pytest.mark.parametrize("recover", [True, False])
def test_background_connect_retries_are_bounded_and_projection_runs_only_once(monkeypatch, recover):
    original_sleep = asyncio.sleep
    backoffs = []

    async def short_sleep(delay):
        backoffs.append(delay)
        await original_sleep(0)

    async def start(self):
        self.status = "unavailable"
        self.failure_type = "TimeoutError"

    async def check(self, **kwargs):
        self.status = "connected" if recover else "unavailable"
        return recover

    async def sync(self, nodes, edges):
        self.is_operational = True

    async def read(self):
        return InMemoryBackendRepository().to_graph_store()

    monkeypatch.setattr("backend.app.main.asyncio.sleep", short_sleep)
    start_mock = AsyncMock(side_effect=start)
    check_mock = AsyncMock(side_effect=check)
    schema = AsyncMock()
    sync_mock = AsyncMock(side_effect=sync)
    # Bind explicit wrappers because AsyncMock does not provide descriptor binding.
    async def wrapped_start(self):
        await start_mock(self)

    async def wrapped_check(self, **kwargs):
        return await check_mock(self, **kwargs)

    async def wrapped_sync(self, nodes, edges):
        await sync_mock(self, nodes, edges)

    monkeypatch.setattr(Neo4jConnection, "start", wrapped_start)
    monkeypatch.setattr(Neo4jConnection, "check", wrapped_check)
    monkeypatch.setattr(Neo4jConnection, "ensure_schema", schema)
    monkeypatch.setattr(Neo4jConnection, "sync_projection", wrapped_sync)
    monkeypatch.setattr(Neo4jConnection, "to_graph_store", read)
    app = make_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/nexus/intelligence/bootstrap").status_code == 200
        assert app.state.neo4j.is_operational is recover
        assert app.state.graph_initialization["attempt"] == (2 if recover else 3)
        assert client.get("/api/v1/graph/stats").status_code == (200 if recover else 503)
    start_mock.assert_awaited_once()
    assert check_mock.await_count == (1 if recover else 2)
    assert schema.await_count == (1 if recover else 0)
    assert sync_mock.await_count == (1 if recover else 0)
    assert backoffs == ([2] if recover else [2, 4])
