import pytest


@pytest.fixture(autouse=True)
def clean_env_for_testing(monkeypatch):
    """Ensure standard tests run in clean deterministic fallback mode without live network calls."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_USE_MOCK_LLM", raising=False)
