"""Real connection smoke test. Never accepts an existing database URI.

Set NEXUS_RUN_NEO4J_SMOKE=1 to create a uniquely named loopback-only container
and volume. Only resources bearing this test's exact ownership label are removed.
No graph records are read from outside that new instance; no application data
is written. Authentication is random, private, and passed through environment.
"""

import asyncio
import os
import re
import secrets
import shutil
import subprocess
import time
import uuid

import pytest

from backend.app.config import Settings
from backend.app.db.neo4j import Neo4jConnection, Neo4jUnavailableError

IMAGE = "neo4j:5.26.30-community"
LABEL = "io.nexus.connection-smoke"


def docker(*args, env=None, timeout=60):
    context = subprocess.run(
        ["docker", "context", "inspect", "--format", "{{.Name}}|{{.Endpoints.docker.Host}}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
    )
    name, separator, host = context.stdout.strip().partition("|")
    if context.returncode or not separator or not host.startswith(("unix://", "npipe://")):
        raise RuntimeError("Smoke test requires a local Docker socket context; remote engines are refused")
    result = subprocess.run(
        ["docker", "--context", name, *args], env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode:
        # Captured output is intentionally not included: it could contain config.
        raise RuntimeError(f"Isolated smoke-test Docker {args[0]} failed")
    return result.stdout.strip()


def remove_owned(resource, owner, *, volume=False):
    prefix = ["volume"] if volume else []
    template = f'{{{{index .Labels "{LABEL}"}}}}' if volume else f'{{{{index .Config.Labels "{LABEL}"}}}}'
    label = docker(*prefix, "inspect", "--format", template, resource)
    if label != owner:
        raise RuntimeError("Refusing to remove a Docker resource without the exact smoke-test owner label")
    if volume:
        docker("volume", "rm", resource)
    else:
        docker("rm", "--force", resource)


@pytest.mark.neo4j_integration
@pytest.mark.skipif(os.getenv("NEXUS_RUN_NEO4J_SMOKE") != "1", reason="Requires explicit isolated Docker smoke-test opt-in")
def test_real_neo4j_connection_and_authentication():
    if shutil.which("docker") is None:
        pytest.fail("BLOCKED: Docker CLI is unavailable")
    docker("version", "--format", "{{.Server.Version}}")
    owner = f"nexus-neo4j-smoke-{uuid.uuid4().hex}"
    volume = f"{owner}-data"
    private = secrets.token_urlsafe(32)
    env = {**os.environ, "NEO4J_AUTH": f"neo4j/{private}"}
    volume_created = container_created = False
    try:
        docker("volume", "create", "--label", f"{LABEL}={owner}", volume)
        volume_created = True
        docker(
            "create", "--name", owner, "--label", f"{LABEL}={owner}",
            "--env", "NEO4J_AUTH", "--publish", "127.0.0.1::7687",
            "--env", "NEO4J_server_memory_heap_initial__size=128m",
            "--env", "NEO4J_server_memory_heap_max__size=256m",
            "--env", "NEO4J_server_memory_pagecache_size=128m",
            "--mount", f"type=volume,source={volume},target=/data",
            IMAGE, env=env, timeout=180,
        )
        container_created = True
        docker("start", owner)
        binding = docker("port", owner, "7687/tcp")
        if not re.fullmatch(r"127\.0\.0\.1:\d+", binding):
            raise RuntimeError("Smoke test requires an isolated loopback Bolt port")

        def config(**overrides):
            return Settings(_env_file=None, **{
                "GRAPH_BACKEND": "neo4j", "NEO4J_URI": f"bolt://{binding}",
                "NEO4J_USER": "neo4j", "NEO4J_PASSWORD": private,
                "NEO4J_DATABASE": "neo4j", "NEO4J_CONNECTION_TIMEOUT": 2,
                "NEO4J_QUERY_TIMEOUT": 2, "NEO4J_FAILURE_POLICY": "degraded", **overrides,
            })

        async def exercise():
            from neo4j import Query

            connection = Neo4jConnection(config())
            try:
                await connection.start()
                deadline = time.monotonic() + 90
                while connection.status != "connected" and time.monotonic() < deadline:
                    await asyncio.sleep(1)
                    await connection.check()
                assert connection.status == "connected", "Isolated Neo4j did not become available"
                records, _, _ = await connection.driver.execute_query(
                    Query("CALL dbms.components() YIELD versions, edition RETURN versions[0] AS version, edition", timeout=2),
                    database_="neo4j", routing_="r",
                )
                assert records[0]["version"] == "5.26.30"
                assert records[0]["edition"] == "community"
                # Exercise the explicit verify_connectivity + selected DB query path.
                assert await connection.check(verify=True)
                for overrides in (
                    {"NEO4J_PASSWORD": secrets.token_urlsafe(32)},
                    {"NEO4J_DATABASE": "nexus-smoke-missing"},
                ):
                    invalid = Neo4jConnection(config(NEO4J_FAILURE_POLICY="required", **overrides))
                    try:
                        with pytest.raises(Neo4jUnavailableError):
                            await invalid.start()
                        assert invalid.status == "closed"
                    finally:
                        await invalid.close()
            finally:
                await connection.close()
            assert connection.status == "closed"

        asyncio.run(exercise())
    finally:
        if container_created:
            remove_owned(owner, owner)
        if volume_created:
            remove_owned(volume, owner, volume=True)
