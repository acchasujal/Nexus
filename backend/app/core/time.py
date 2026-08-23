"""backend/app/core/time.py

Injectable UTC clock abstraction for all deterministic engine calculations.

Why this module exists:
  - All engines (clock, dependency, escalation) need a reference time.
  - Using `datetime.now()` directly makes tests non-deterministic and time-zone
    fragile.
  - This module provides a single interface that production code and tests both
    use, making time-freezing simple and safe.

Usage in application code:
    from backend.app.core.time import utc_now, SystemClock, FrozenClock

    # Production: always use the injected clock, never datetime.now() directly.
    clock = SystemClock()
    now = clock.now()

    # Tests: freeze time at a known point.
    clock = FrozenClock(datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc))
    engine = ClockEngine(reference_time=clock.now())
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


# ── Public helpers ─────────────────────────────────────────────────────────────


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    This is the ONLY place `datetime.now(timezone.utc)` should be called in
    production code.  Engines and services must accept an injected clock so
    tests can freeze time without monkeypatching.
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Return dt as UTC-aware; if naive, attach UTC tzinfo without conversion.

    Following the plan's convention: all timestamps are UTC-aware ISO-8601.
    Naive datetimes in internal code are a bug; this helper surfaces them
    without silently shifting calendar values.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── Clock interface ────────────────────────────────────────────────────────────


class Clock(ABC):
    """Abstract clock interface.  Inject this into engines and services instead
    of calling datetime.now() directly."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current reference time as a UTC-aware datetime."""
        ...


class SystemClock(Clock):
    """Production clock: returns the real UTC wall time on every call."""

    def now(self) -> datetime:
        return utc_now()


class FrozenClock(Clock):
    """Test clock: always returns the same datetime.

    Args:
        frozen_time: A UTC-aware datetime to return on every `now()` call.

    Raises:
        ValueError: If frozen_time is not timezone-aware.
    """

    def __init__(self, frozen_time: datetime) -> None:
        if frozen_time.tzinfo is None:
            raise ValueError(
                f"FrozenClock requires a timezone-aware datetime; got {frozen_time!r}.  "
                "Pass e.g. datetime(2026, 7, 18, tzinfo=timezone.utc)."
            )
        self._frozen = frozen_time

    def now(self) -> datetime:
        return self._frozen
