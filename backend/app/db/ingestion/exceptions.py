"""Exceptions raised by ingestion validation."""


class CsvValidationError(ValueError):
	"""Raised when a CSV value cannot be safely normalized or parsed."""

__all__ = ["CsvValidationError"]
