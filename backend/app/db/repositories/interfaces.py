"""backend/app/db/repositories/interfaces.py

Abstract repository interfaces for CaseClock domain entities.

These interfaces decouple application services from the persistence layer.
Phase 1 uses InMemoryBackendRepository (already implemented).
Phase 2 plugs in Catalyst Data Store repositories that implement these ABCs.
Phase 4 routes all service calls through these interfaces.

Design rules (from BACKEND_IMPLEMENTATION_PLAN.md §9):
  - Repositories own persistence reads/writes only — no business rules.
  - Authorization policy decisions are not made here.
  - All list methods take optional cursor/limit for future pagination.
  - Raises DomainError subclasses; callers translate to HTTP in api/ layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


# ── Canonical domain record types ─────────────────────────────────────────────
# Using typed dicts here rather than Pydantic so that the repository layer
# does not depend on the API contract layer.  Services map to contract types.

class CaseRecord:
    """Minimal data-transfer object for a Case entity row."""
    __slots__ = ("id", "fir_number", "police_station", "district",
                 "offence_category", "case_stage", "reported_at",
                 "created_at", "updated_at")

    def __init__(self, **kwargs: Any) -> None:
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


class DependencyRecord:
    """Data-transfer object for a Dependency entity row."""
    __slots__ = ("id", "case_id", "dependency_type", "name", "status",
                 "requested_at", "due_at", "resolved_at",
                 "assigned_to_officer_id", "created_at", "updated_at")

    def __init__(self, **kwargs: Any) -> None:
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


class ClockInstanceRecord:
    """Data-transfer object for a ClockInstance entity row."""
    __slots__ = ("id", "case_id", "clock_type", "start_date", "deadline_date",
                 "bnss_reference", "rule_version", "created_at", "updated_at")

    def __init__(self, **kwargs: Any) -> None:
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


class EscalationRecord:
    """Data-transfer object for an EscalationEvent entity row."""
    __slots__ = ("id", "case_id", "trigger_kind", "source_entity_id",
                 "rule_version", "threshold_date", "reason",
                 "routed_to_rank", "routed_to_officer_id",
                 "triggered_at", "resolved", "resolved_at",
                 "created_at", "updated_at")

    def __init__(self, **kwargs: Any) -> None:
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


class AuditRecord:
    """Data-transfer object for an AuditEvent entity row."""
    __slots__ = ("id", "event_type", "actor_id", "case_id", "entity_type",
                 "entity_id", "metadata", "request_id", "occurred_at")

    def __init__(self, **kwargs: Any) -> None:
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))


# ── Repository interfaces ──────────────────────────────────────────────────────


class CaseRepository(ABC):
    """Read access to Case entities and their associations."""

    @abstractmethod
    def get_by_id(self, case_id: str) -> CaseRecord | None:
        """Return the Case with the given ID, or None if absent."""
        ...

    @abstractmethod
    def list_by_station(
        self,
        station: str | None = None,
        district: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[CaseRecord]:
        """Return cases scoped to station/district, ordered by reported_at desc."""
        ...

    @abstractmethod
    def get_clocks(self, case_id: str) -> list[ClockInstanceRecord]:
        """Return all ClockInstance rows for the given case."""
        ...

    @abstractmethod
    def get_dependencies(self, case_id: str) -> list[DependencyRecord]:
        """Return all Dependency rows for the given case."""
        ...


class DependencyRepository(ABC):
    """Read/write access to Dependency entities."""

    @abstractmethod
    def get_by_id(self, dependency_id: str) -> DependencyRecord | None:
        ...

    @abstractmethod
    def update_status(
        self,
        dependency_id: str,
        new_status: str,
        resolved_at: datetime | None,
        actor_id: str | None,
    ) -> DependencyRecord:
        """Update status atomically.  Raises ConflictError on stale version."""
        ...


class EscalationRepository(ABC):
    """Idempotent read/write access to EscalationEvent entities."""

    @abstractmethod
    def upsert(self, record: EscalationRecord) -> EscalationRecord:
        """Insert or update by the natural trigger key (idempotent)."""
        ...

    @abstractmethod
    def list_for_case(self, case_id: str, resolved: bool | None = None) -> list[EscalationRecord]:
        ...

    @abstractmethod
    def resolve(self, escalation_id: str, resolved_at: datetime) -> EscalationRecord:
        ...


class AuditRepository(ABC):
    """Append-only audit trail."""

    @abstractmethod
    def append(self, record: AuditRecord) -> None:
        """Write one audit event.  Never raises on individual row failure (best effort)."""
        ...

    @abstractmethod
    def list_events(
        self,
        limit: int = 100,
        case_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        cursor: str | None = None,
    ) -> list[AuditRecord]:
        ...
