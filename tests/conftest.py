import os

import pytest

# Configure before collection imports main.py and constructs its module-level app.
# Integration tests use separate opt-in variables and create their own containers.
os.environ.update({
    "NEXUS_REPOSITORY": "memory", "GRAPH_BACKEND": "memory", "DATABASE_URL": "",
    "STATE_PATH": "", "ENVIRONMENT": "development", "AUTH_MODE": "demo",
    "NEO4J_URI": "", "NEO4J_USER": "", "NEO4J_PASSWORD": "",
    "NEO4J_DATABASE": "neo4j", "NEO4J_FAILURE_POLICY": "required",
    "NEO4J_CONNECTION_TIMEOUT": "5", "NEO4J_QUERY_TIMEOUT": "10", "JWT_SECRET_KEY": "",
    "ARTIFACT_PATH": "artifacts/nexus_graph/nexus_graph.json",
    "GROQ_API_KEY": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "LLM_API_KEY": "",
    "PYTHON_DOTENV_DISABLED": "1",
})

from backend.app.config import Settings

Settings.model_config["env_file"] = None


@pytest.fixture(autouse=True)
def clean_env_for_testing(monkeypatch):
    """Ensure standard tests run in clean deterministic fallback mode without live network calls."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_USE_MOCK_LLM", raising=False)
