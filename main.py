"""Root entrypoint for FastAPI Cloud / FastAPI CLI discovery.
Imports and exposes the NEXUS FastAPI application instance.
"""

from backend.app.main import app

__all__ = ["app"]
