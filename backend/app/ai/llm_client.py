"""backend/app/ai/llm_client.py

Provider-agnostic LLM Client interface with Real Provider and Test Mock implementations.
Enforces strict separation:
  - RealLLMClient: Active in production when real API keys/endpoints are supplied.
  - DeterministicMockLLMClient: Active ONLY during automated tests and CI.
  - Unconfigured: Returns None to trigger immediate deterministic fallback.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Protocol, runtime_checkable

from backend.app.ai.schemas import (
    ChatMessage,
    LLMRequest,
    LLMResponse,
    ToolCall,
    UsageMetadata,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class BaseLLMClient(Protocol):
    """Protocol defining the standard interface for NEXUS LLM clients."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def generate(self, request: LLMRequest) -> LLMResponse:
        ...


class RealLLMClient:
    """Production-grade LLM client for OpenAI, Gemini (via OpenAI compatibility), and Ollama endpoints."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        provider_name: str = "openai_compatible",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._provider_name = provider_name
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        # Build messages payload
        messages_payload = []
        for msg in request.messages:
            m_dict: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m_dict["name"] = msg.name
            if msg.metadata.get("tool_call_id"):
                m_dict["tool_call_id"] = msg.metadata["tool_call_id"]
            if msg.metadata.get("tool_calls"):
                m_dict["tool_calls"] = msg.metadata["tool_calls"]
            messages_payload.append(m_dict)

        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": messages_payload,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = "auto"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            choice = resp_data.get("choices", [{}])[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")

            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    fn = tc.get("function", {})
                    args = {}
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        pass
                    tool_calls.append(
                        ToolCall(
                            name=fn.get("name", ""),
                            arguments=args,
                            call_id=tc.get("id"),
                        )
                    )

            usage = None
            if "usage" in resp_data:
                usage = UsageMetadata(
                    prompt_tokens=resp_data["usage"].get("prompt_tokens", 0),
                    completion_tokens=resp_data["usage"].get("completion_tokens", 0),
                    total_tokens=resp_data["usage"].get("total_tokens", 0),
                )

            return LLMResponse(
                content=message.get("content"),
                tool_calls=tool_calls,
                usage=usage,
                finish_reason=finish_reason,
                raw_metadata={"model": resp_data.get("model")},
            )

        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            logger.error("LLM Provider HTTP Error (%s): %s", exc.code, err_body)
            raise RuntimeError(f"LLM Provider returned HTTP {exc.code}: {err_body}") from exc
        except Exception as exc:
            logger.error("LLM Provider connection failed: %s", exc)
            raise RuntimeError(f"LLM Provider invocation failed: {exc}") from exc


class DeterministicMockLLMClient:
    """Mock LLM client strictly for automated unit tests, CI benchmarks, and test runners."""

    def __init__(self, model_name: str = "nexus-mock-model") -> None:
        self._model = model_name

    @property
    def provider_name(self) -> str:
        return "mock_test_provider"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        # Check if the last message is a tool execution result
        last_msg = request.messages[-1] if request.messages else None

        if last_msg and last_msg.role == "tool":
            # Synthesis step after tool execution
            return LLMResponse(
                content=f"Based on the verified deterministic graph intelligence results: {last_msg.content}",
                tool_calls=[],
                usage=UsageMetadata(prompt_tokens=50, completion_tokens=30, total_tokens=80),
                finish_reason="stop",
            )

        # Inspect user query for tool calling test triggers
        user_query = ""
        for m in reversed(request.messages):
            if m.role == "user":
                user_query = m.content.lower()
                break

        if "path" in user_query or "connect" in user_query or "between" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="find_shortest_path",
                        arguments={"source_id": "CASE-141", "target_id": "CASE-207"},
                        call_id="call-mock-path-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "alias" in user_query or "resolve" in user_query or "suspect" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="resolve_person_identity",
                        arguments={"full_name": "Rafiq Khan", "phone_number": "9845011223"},
                        call_id="call-mock-resolve-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "broker" in user_query or "kingpin" in user_query or "bridge" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="detect_bridge_brokers",
                        arguments={},
                        call_id="call-mock-bridge-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "community" in user_query or "syndicate" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="detect_communities",
                        arguments={"resolution_state": "after"},
                        call_id="call-mock-comm-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "case" in user_query or "fir" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="get_case_dossier",
                        arguments={"case_id": "CASE-141"},
                        call_id="call-mock-case-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "money" in user_query or "transfer" in user_query or "layering" in user_query:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        name="detect_financial_layering",
                        arguments={},
                        call_id="call-mock-fin-01",
                    )
                ],
                finish_reason="tool_calls",
            )
        else:
            return LLMResponse(
                content="NEXUS Intelligence Copilot is active and ready to query graph intelligence files.",
                tool_calls=[],
                finish_reason="stop",
            )


def get_llm_client(force_mock_for_test: bool = False) -> BaseLLMClient | None:
    """Factory retrieving the configured LLM client.
    
    Resolution order:
      1. force_mock_for_test or NEXUS_USE_MOCK_LLM=true -> DeterministicMockLLMClient (Test only).
      2. Check GEMINI_API_KEY, LLM_API_KEY, NEXUS_LLM_API_KEY, OPENAI_API_KEY.
      3. If no key -> returns None (triggering immediate deterministic Copilot fallback).
      4. Configures Gemini / OpenAI OpenAI-compatible endpoint with configurable model.
    """
    if force_mock_for_test or os.environ.get("NEXUS_USE_MOCK_LLM", "").lower() in ("true", "1"):
        return DeterministicMockLLMClient()

    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    generic_key = os.environ.get("LLM_API_KEY") or os.environ.get("NEXUS_LLM_API_KEY")

    api_key = gemini_key or generic_key or openai_key
    if not api_key:
        return None

    provider = (os.environ.get("LLM_PROVIDER") or os.environ.get("NEXUS_LLM_PROVIDER", "")).lower()

    # Determine base_url, model, and provider_name
    if provider == "openai" or (openai_key and not gemini_key and not provider):
        base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("NEXUS_LLM_BASE_URL") or "https://api.openai.com/v1"
        model = os.environ.get("LLM_MODEL") or os.environ.get("NEXUS_LLM_MODEL") or "gpt-4o-mini"
        provider_name = "openai"
    else:
        # Default to Google Gemini OpenAI-compatible endpoint
        base_url = (
            os.environ.get("LLM_BASE_URL")
            or os.environ.get("NEXUS_LLM_BASE_URL")
            or "https://generativelanguage.googleapis.com/v1beta/openai"
        )
        model = os.environ.get("LLM_MODEL") or os.environ.get("NEXUS_LLM_MODEL") or "gemini-2.5-flash"
        provider_name = provider or "gemini"

    return RealLLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        provider_name=provider_name,
    )
