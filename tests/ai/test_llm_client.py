"""tests/ai/test_llm_client.py

Unit tests for LLM client resolution, Gemini OpenAI-compatible configuration,
tool-call message serialization, response parsing, and error fallback.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app.ai.llm_client import (
    DeterministicMockLLMClient,
    RealLLMClient,
    get_llm_client,
)
from backend.app.ai.schemas import ChatMessage, LLMRequest, ToolCall


def test_mock_llm_client_generation():
    client = DeterministicMockLLMClient()
    assert client.provider_name == "mock_test_provider"

    # User query requesting shortest path
    req = LLMRequest(
        messages=[ChatMessage(role="user", content="How are CASE-141 and CASE-207 connected?")]
    )
    res = client.generate(req)
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "find_shortest_path"


def test_get_llm_client_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_USE_MOCK_LLM", raising=False)

    client = get_llm_client()
    assert client is None


def test_get_llm_client_groq_detection(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-key-12345")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    client = get_llm_client()
    assert isinstance(client, RealLLMClient)
    assert client.provider_name == "groq"
    assert client.model_name == "openai/gpt-oss-120b"
    assert client._base_url == "https://api.groq.com/openai/v1"


def test_get_llm_client_gemini_detection(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-12345")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    client = get_llm_client()
    assert isinstance(client, RealLLMClient)
    assert client.provider_name == "gemini"
    assert client.model_name == "gemini-2.5-flash"
    assert client._base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_get_llm_client_custom_gemini_model_and_url(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-12345")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom-gateway.local/v1")

    client = get_llm_client()
    assert isinstance(client, RealLLMClient)
    assert client.provider_name == "gemini"
    assert client.model_name == "gemini-2.5-flash"
    assert client._base_url == "https://custom-gateway.local/v1"


def test_real_llm_client_request_serialization():
    client = RealLLMClient(
        api_key="test-key",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-2.5-flash",
        provider_name="gemini",
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "find_shortest_path",
                "description": "Find path between entities",
                "parameters": {"type": "object", "properties": {"source_id": {"type": "string"}}},
            },
        }
    ]

    req = LLMRequest(
        messages=[
            ChatMessage(role="system", content="You are NEXUS Copilot."),
            ChatMessage(
                role="assistant",
                content="",
                metadata={
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "find_shortest_path", "arguments": '{"source_id": "CASE-141"}'},
                        }
                    ]
                },
            ),
            ChatMessage(
                role="tool",
                name="find_shortest_path",
                content='{"success": true, "data": {"hops": 2}}',
                metadata={"tool_call_id": "call_123"},
            ),
        ],
        tools=tools,
        temperature=0.0,
    )

    fake_response = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "The cases connect in 2 hops via shared phone +91 98450 11223.",
                },
                "finish_reason": "stop",
            }
        ],
        "model": "gemini-2.5-flash",
        "usage": {"prompt_tokens": 150, "completion_tokens": 25, "total_tokens": 175},
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        res = client.generate(req)

        assert res.content == "The cases connect in 2 hops via shared phone +91 98450 11223."
        assert res.finish_reason == "stop"
        assert res.usage.total_tokens == 175

        # Verify outgoing HTTP request headers and body
        call_args = mock_urlopen.call_args
        http_req = call_args[0][0]
        assert http_req.get_header("Authorization") == "Bearer test-key"
        assert http_req.get_header("Content-type") == "application/json"

        body = json.loads(http_req.data.decode("utf-8"))
        assert body["model"] == "gemini-2.5-flash"
        assert len(body["messages"]) == 3
        assert body["messages"][1]["tool_calls"][0]["id"] == "call_123"
        assert body["messages"][2]["tool_call_id"] == "call_123"
        assert len(body["tools"]) == 1


def test_real_llm_client_tool_call_response_parsing():
    client = RealLLMClient(
        api_key="test-key",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-2.5-flash",
    )

    req = LLMRequest(messages=[ChatMessage(role="user", content="Find connection")])

    fake_tool_call_response = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_gemini_abc",
                            "type": "function",
                            "function": {
                                "name": "find_shortest_path",
                                "arguments": json.dumps({"source_id": "CASE-141", "target_id": "CASE-207"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "model": "gemini-2.5-flash",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_tool_call_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.generate(req)
        assert len(res.tool_calls) == 1
        assert res.tool_calls[0].name == "find_shortest_path"
        assert res.tool_calls[0].arguments["source_id"] == "CASE-141"
        assert res.tool_calls[0].call_id == "call_gemini_abc"
