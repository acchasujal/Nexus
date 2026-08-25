"""tests/test_system_health.py

Integration tests for NEXUS cloud deployment health, readiness, and monitoring probes.
Tests:
  - GET /health (Liveness probe for Render / Kubernetes)
  - GET /ready (Readiness probe verifying repository & graph storage)
  - GET /api/v1/health (Prefixed health probe)
  - GET /api/v1/system/status (Detailed system and telemetry breakdown)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo)
    return TestClient(app)


def test_root_health_liveness_probe(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "ok")
    assert "nexus" in data["service"].lower()


def test_prefixed_health_probe(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "ok")


def test_root_readiness_probe(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["total_nodes"] > 0
    assert data["total_edges"] > 0


def test_system_status_telemetry(client: TestClient) -> None:
    resp = client.get("/api/v1/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["total_cases"] > 0
    assert data["evidence_hash_version"] == "SHA256-BSA-S63-V1"
