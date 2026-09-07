"""Connection/lifespan tests use explicit doubles; real Bolt coverage is opt-in."""

import asyncio
import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.neo4j import Neo4jConnection, Neo4jUnavailableError
from backend.app.main import create_app


def settings(**overrides):
    return Settings(_env_file=None, **{
        "GRAPH_BACKEND": "neo4j", "NEO4J_URI": "bolt://127.0.0.1:7687",
        "NEO4J_USER": "neo4j", "NEO4J_PASSWORD": secrets.token_urlsafe(24),
        "NEO4J_DATABASE": "nexus", **overrides,
    })


@pytest.fixture
def driver_factory(monkeypatch):
    import neo4j

    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    driver.execute_query = AsyncMock(return_value=([{"ok": 1}], None, ["ok"]))
    driver.close = AsyncMock()
    factory = MagicMock(return_value=driver)
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", factory)
    return factory


def app_for(cfg):
    return create_app(repository=InMemoryBackendRepository(), settings=cfg)


def test_memory_mode_never_creates_driver(driver_factory):
    app = app_for(Settings(_env_file=None))
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/ready").json()["graph"]["backend"] == "memory"
        assert client.get("/api/v1/nexus/network").status_code == 200
    driver_factory.assert_not_called()


@pytest.mark.parametrize("overrides", [
    {"GRAPH_BACKEND": "unknown"}, {"NEO4J_URI": ""}, {"NEO4J_USER": " "},
    {"NEO4J_PASSWORD": ""}, {"NEO4J_DATABASE": ""}, {"NEO4J_DATABASE": "system"},
    {"NEO4J_URI": "http://localhost:7474"}, {"NEO4J_URI": "bolt://localhost:0"},
    {"NEO4J_URI": "bolt://localhost/path"}, {"NEO4J_URI": "bolt://localhost:99999"},
    {"NEO4J_CONNECTION_TIMEOUT": 0}, {"NEO4J_QUERY_TIMEOUT": -1},
    {"NEO4J_QUERY_TIMEOUT": float("nan")}, {"NEO4J_FAILURE_POLICY": "ignore"},
])
def test_invalid_neo4j_settings(overrides):
    with pytest.raises(ValidationError):
        settings(**overrides)


def test_credentials_redacted_from_configuration_errors_and_serialization():
    private = secrets.token_urlsafe(24)
    cfg = settings(NEO4J_PASSWORD=private, DATABASE_URL=private, JWT_SECRET_KEY=private)
    assert private not in repr(cfg)
    assert private not in cfg.model_dump_json()
    with pytest.raises(ValidationError) as caught:
        settings(NEO4J_URI=f"bolt://neo4j:{private}@localhost:7687", NEO4J_PASSWORD=private)
    assert private not in str(caught.value)


def test_no_committed_authentication_defaults():
    cfg = Settings(_env_file=None)
    assert cfg.database_url == ""
    assert cfg.neo4j_password.get_secret_value() == ""
    assert len(cfg.jwt_secret_key) >= 32
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, ENVIRONMENT="production")
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, NEXUS_REPOSITORY="postgres")


def test_single_driver_database_probe_and_shutdown(driver_factory):
    cfg = settings(NEO4J_QUERY_TIMEOUT=3, NEO4J_CONNECTION_TIMEOUT=2)
    app = app_for(cfg)
    hooks = []
    app.router.on_startup.append(lambda: hooks.append("startup"))
    app.router.on_shutdown.append(lambda: hooks.append("shutdown"))
    with TestClient(app) as client:
        assert app.state.neo4j.driver is driver_factory.return_value
        for path in ("/health", "/api/v1/health"):
            assert client.get(path).status_code == 200
        result = client.get("/ready")
        # Connectivity succeeds, but this step has no operational projection yet.
        assert result.status_code == 503
        assert result.json()["dependencies_ready"] is True
        assert result.json()["graph"]["connection"] == "connected"
        assert result.json()["graph"]["operational"] is False
        for path in ("/api/v1/nexus/network", "/api/v1/graph/stats", "/api/v1/entities"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["details"]["projection"] == "not_implemented"
        assert client.post("/api/v1/nexus/demo/reset").status_code == 503
    driver_factory.assert_called_once()
    driver = driver_factory.return_value
    driver.verify_connectivity.assert_awaited_once()
    for call in driver.execute_query.call_args_list:
        assert call.kwargs["database_"] == "nexus"
        assert call.kwargs["routing_"] == "r"
        assert call.args[0].timeout == 3
    assert driver_factory.call_args.kwargs["connection_timeout"] == 2
    driver.close.assert_awaited_once()
    assert app.state.neo4j.status == "closed"
    assert hooks == ["startup", "shutdown"]


@pytest.mark.parametrize("stage", ["verify_connectivity", "execute_query"])
def test_required_startup_failure_closes_driver_without_secret_logs(driver_factory, caplog, stage):
    cfg = settings()
    private = cfg.neo4j_password.get_secret_value()
    getattr(driver_factory.return_value, stage).side_effect = RuntimeError(private)
    with pytest.raises(Neo4jUnavailableError) as caught:
        with TestClient(app_for(cfg)):
            pytest.fail("Required dependency failure must abort startup")
    assert private not in str(caught.value)
    assert private not in caplog.text
    driver_factory.return_value.close.assert_awaited_once()


def test_degraded_policy_exposes_failure_and_recovers_same_pool(driver_factory, caplog):
    cfg = settings(NEO4J_FAILURE_POLICY="degraded")
    private = cfg.neo4j_password.get_secret_value()
    driver = driver_factory.return_value
    driver.execute_query.side_effect = RuntimeError(private)
    with TestClient(app_for(cfg)) as client:
        result = client.get("/ready")
        assert result.status_code == 200
        assert result.json()["status"] == "degraded"
        assert result.json()["graph"]["connection"] == "unavailable"
        assert private not in result.text
        assert client.get("/api/v1/nexus/network").status_code == 503
        driver.execute_query.side_effect = None
        result = client.get("/ready").json()
        assert result["graph"]["connection"] == "connected"
        assert result["graph"]["operational"] is False
        driver.execute_query.side_effect = RuntimeError(private)
        assert client.get("/health").status_code == 200
    assert private not in caplog.text
    driver_factory.assert_called_once()
    driver.close.assert_awaited_once()


def test_required_dependency_lost_after_start(driver_factory):
    with TestClient(app_for(settings())) as client:
        driver_factory.return_value.execute_query.side_effect = RuntimeError("offline")
        result = client.get("/ready")
        assert result.status_code == 503
        assert result.json()["dependencies_ready"] is False
        assert client.get("/health").status_code == 200


def test_later_startup_hook_failure_still_closes_driver(driver_factory):
    app = app_for(settings())

    async def fail():
        raise RuntimeError("synthetic startup failure")

    app.router.on_startup.append(fail)
    with pytest.raises(RuntimeError, match="synthetic startup failure"):
        with TestClient(app):
            pass
    driver_factory.return_value.close.assert_awaited_once()


def test_cancelled_startup_closes_driver(driver_factory):
    driver_factory.return_value.verify_connectivity.side_effect = asyncio.CancelledError()
    connection = Neo4jConnection(settings())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(connection.start())
    driver_factory.return_value.close.assert_awaited_once()


def test_shutdown_error_is_sanitized(driver_factory, caplog):
    cfg = settings()
    private = cfg.neo4j_password.get_secret_value()
    driver_factory.return_value.close.side_effect = RuntimeError(private)
    app = app_for(cfg)
    with TestClient(app):
        pass
    assert private not in caplog.text
    assert "cleanup failed" in caplog.text
    assert app.state.neo4j.status == "cleanup_failed"


def test_probe_failure_before_lifespan_does_not_create_driver(driver_factory):
    client = TestClient(app_for(settings()))
    result = client.get("/ready")
    assert result.status_code == 503
    assert result.json()["graph"]["connection"] == "not_started"
    driver_factory.assert_not_called()


def test_connection_creation_failure_is_sanitized(driver_factory, caplog):
    cfg = settings()
    private = cfg.neo4j_password.get_secret_value()
    driver_factory.side_effect = RuntimeError(private)
    with pytest.raises(Neo4jUnavailableError) as caught:
        with TestClient(app_for(cfg)):
            pass
    assert private not in str(caught.value)
    assert private not in caplog.text


def test_client_deadline_closes_hung_startup(driver_factory):
    async def hung():
        await asyncio.Event().wait()

    driver_factory.return_value.verify_connectivity.side_effect = hung
    connection = Neo4jConnection(settings(NEO4J_CONNECTION_TIMEOUT=0.01, NEO4J_QUERY_TIMEOUT=0.01))
    with pytest.raises(Neo4jUnavailableError):
        asyncio.run(connection.start())
    driver_factory.return_value.close.assert_awaited_once()


def test_legacy_postgres_fallback_is_unready_and_neo4j_never_falls_back(monkeypatch, driver_factory, caplog):
    from backend.app import main

    private = secrets.token_urlsafe(24)
    monkeypatch.setattr(main, "PostgresBackendRepository", MagicMock(side_effect=RuntimeError(private)))
    cfg = settings(GRAPH_BACKEND="memory", NEXUS_REPOSITORY="postgres", DATABASE_URL="postgresql://unused")
    with TestClient(main.create_app(settings=cfg)) as client:
        assert client.get("/ready").status_code == 503
        assert client.get("/health").status_code == 200
    with pytest.raises(RuntimeError, match="no fallback"):
        main.create_app(settings=settings(NEXUS_REPOSITORY="postgres", DATABASE_URL="postgresql://unused"))
    assert private not in caplog.text
    driver_factory.assert_not_called()


def test_postgres_failure_is_unready_and_probe_runs_off_event_loop(monkeypatch):
    import threading
    from backend.app.api import system_routes
    from backend.app.db.postgres import PostgresBackendRepository

    app = app_for(Settings(_env_file=None))
    # Replace after construction so no database constructor or SQL can run.
    repo = object.__new__(PostgresBackendRepository)
    repo.nodes, repo.edges = {}, []
    app.state.repository = repo
    observed = []

    def unavailable(_repo):
        observed.append(threading.current_thread().name)
        return False

    monkeypatch.setattr(system_routes, "_postgres_available", unavailable)
    with TestClient(app) as client:
        result = client.get("/ready")
        assert result.status_code == 503
        assert result.json()["storage"] == "postgres"
        assert result.json()["storage_available"] is False
        assert client.get("/health").status_code == 200
    assert observed == ["AnyIO worker thread"]
