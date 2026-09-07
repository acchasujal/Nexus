"""Async connection foundation only: no graph projection or memory fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from backend.app.config import Settings

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jUnavailableError(RuntimeError):
    """Sanitized connection failure safe to surface during application startup."""


class Neo4jConnection:
    """One driver/pool per application lifespan (one app per worker process).

    Sessions/queries are asynchronous. Never create drivers per request or share
    them across event loops. A degraded connection reuses its pool on later probes.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None
        self.status = "disabled" if settings.graph_backend == "memory" else "not_started"

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise Neo4jUnavailableError("Neo4j driver is not available")
        return self._driver

    async def start(self) -> None:
        if self._settings.graph_backend == "memory":
            return
        if self._driver is not None:
            raise RuntimeError("Neo4j connection already started")
        try:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password.get_secret_value()),
                connection_timeout=self._settings.neo4j_connection_timeout,
                connection_acquisition_timeout=self._settings.neo4j_connection_timeout,
                max_transaction_retry_time=0,
                telemetry_disabled=True,
            )
            available = await self.check(verify=True)
        except asyncio.CancelledError:
            await self.close()
            raise
        except Exception:
            # Never log driver exceptions, URIs, settings or authentication payloads.
            self.status = "unavailable"
            available = False
        if not available and self._settings.neo4j_failure_policy == "required":
            await self.close()
            raise Neo4jUnavailableError("Required Neo4j connection is unavailable") from None

    async def check(self, *, verify: bool = False) -> bool:
        if self._settings.graph_backend == "memory":
            return True
        if self._driver is None:
            return False
        try:
            from neo4j import Query

            # Server query timeout plus a client deadline bounds connection/routing
            # and query execution, including a hung or unavailable dependency.
            deadline = 2 * self._settings.neo4j_connection_timeout + self._settings.neo4j_query_timeout
            async with asyncio.timeout(deadline):
                if verify:
                    await self._driver.verify_connectivity()
                records, _, _ = await self._driver.execute_query(
                    Query("RETURN 1 AS ok", timeout=self._settings.neo4j_query_timeout),
                    database_=self._settings.neo4j_database,
                    routing_="r",
                )
                if len(records) != 1 or records[0]["ok"] != 1:
                    raise Neo4jUnavailableError("Unexpected connectivity probe result")
            self.status = "connected"
            return True
        except asyncio.CancelledError:
            self.status = "unavailable"
            raise
        except Exception:
            self.status = "unavailable"
            logger.warning("Neo4j connectivity probe failed; connection unavailable")
            return False

    async def close(self) -> None:
        driver, self._driver = self._driver, None
        if driver is not None:
            try:
                await driver.close()
            except Exception:
                self.status = "cleanup_failed"
                logger.warning("Neo4j driver cleanup failed")
                return
        if self._settings.graph_backend == "neo4j" and self.status != "cleanup_failed":
            self.status = "closed"
