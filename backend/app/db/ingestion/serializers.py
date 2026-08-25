"""JSON serialization helpers for ingestion outputs."""

from __future__ import annotations

from typing import Any


def to_json_value(value: Any) -> Any:
    """Convert a Pydantic model to JSON-compatible data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


__all__ = ["to_json_value"]
