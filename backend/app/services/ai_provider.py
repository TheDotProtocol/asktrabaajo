"""Provider-neutral AI abstraction for Athena (Phase 14).

The business logic never imports the OpenAI SDK directly and never assumes
a provider. ``get_provider()`` returns a configured provider or ``None``;
with ``ai_provider = none`` Athena fails safely with
``AI_PROVIDER_UNAVAILABLE`` — it never fabricates responses.

Only capabilities Phase 14 actually uses are implemented:
TEXT_GENERATION, STRUCTURED_OUTPUT (client-side schema validation), and
TOOL_CALLING (registered tools only). Provider credentials are
server-side environment variables; they never reach the frontend, logs,
or database records.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.enums import (
    AI_CAPABILITY_STRUCTURED_OUTPUT,
    AI_CAPABILITY_TEXT_GENERATION,
    AI_CAPABILITY_TOOL_CALLING,
    AI_CAPABILITIES,
    AI_ERROR_CONTEXT_LIMIT_EXCEEDED,
    AI_ERROR_INTERNAL,
    AI_ERROR_OUTPUT_INVALID,
    AI_ERROR_PROVIDER_TIMEOUT,
    AI_ERROR_PROVIDER_UNAVAILABLE,
    AI_ERROR_RATE_LIMITED,
)


class AIProviderError(AppError):
    """Provider-neutral error surfaced to Athena (never provider internals)."""

    status_code = 502

    def __init__(self, code: str, message: str, *, status_code: int = 502) -> None:
        super().__init__(message, status_code=status_code, code=code)


def provider_unavailable() -> AIProviderError:
    return AIProviderError(
        AI_ERROR_PROVIDER_UNAVAILABLE,
        "The AI assistant is temporarily unavailable. Please try again later.",
    )


@dataclass
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: Optional[float] = None


@dataclass
class AIToolCall:
    id: str
    name: str
    arguments: Dict = field(default_factory=dict)


@dataclass
class AIResponse:
    content: Optional[str] = None
    tool_calls: List[AIToolCall] = field(default_factory=list)
    model: Optional[str] = None
    usage: AIUsage = field(default_factory=AIUsage)
    finish_reason: Optional[str] = None


class AIProvider:
    """Protocol for an Athena provider.

    ``capabilities`` declares which capabilities the provider actually
    supports; Athena must check before requesting a capability.
    """

    name: str = "abstract"
    capabilities: set = set()

    def chat(
        self,
        messages: List[Dict],
        *,
        tools: Optional[List[Dict]] = None,
        response_schema=None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AIResponse:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI adapter. Requires OPENAI_API_KEY; import is lazy so the app
    boots safely without the SDK/key."""

    name = "openai"
    capabilities = {
        AI_CAPABILITY_TEXT_GENERATION,
        AI_CAPABILITY_STRUCTURED_OUTPUT,
        AI_CAPABILITY_TOOL_CALLING,
    }

    def __init__(self) -> None:
        import openai

        settings = get_settings()
        if not settings.openai_api_key:
            raise AIProviderError(
                AI_ERROR_PROVIDER_UNAVAILABLE,
                "AI provider is not configured.",
            )
        self._client = openai.OpenAI(api_key=settings.openai_api_key)
        self._model = settings.ai_openai_model

    def chat(
        self,
        messages: List[Dict],
        *,
        tools: Optional[List[Dict]] = None,
        response_schema=None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AIResponse:
        if AI_CAPABILITY_TOOL_CALLING not in self.capabilities and tools:
            raise AIProviderError(
                AI_ERROR_OUTPUT_INVALID, "Provider does not support tool calling."
            )
        kwargs: Dict = {"model": self._model, "messages": messages, "temperature": temperature}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        started = time.monotonic()
        try:
            raw = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # provider outage / timeout / rate limit
            code = AI_ERROR_PROVIDER_UNAVAILABLE
            status = 502
            if "timeout" in type(exc).__name__.lower() or getattr(exc, "code", "") == "timeout":
                code = AI_ERROR_PROVIDER_TIMEOUT
            elif getattr(exc, "status_code", None) == 429:
                code = AI_ERROR_RATE_LIMITED
                status = 429
            raise AIProviderError(code, "The AI assistant is temporarily unavailable.", status_code=status)
        latency_ms = int((time.monotonic() - started) * 1000)

        try:
            content = raw.choices[0].message.content if raw.choices else None
            tool_calls = []
            for tc in (raw.choices[0].message.tool_calls or []) if raw.choices else []:
                args = {}
                if tc.function and tc.function.arguments:
                    import json

                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except ValueError:
                        args = {}
                tool_calls.append(AIToolCall(id=tc.id, name=tc.function.name, arguments=args))
            usage = AIUsage(
                prompt_tokens=getattr(raw.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(raw.usage, "completion_tokens", 0) or 0,
            )
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            return AIResponse(
                content=content,
                tool_calls=tool_calls,
                model=getattr(raw, "model", None),
                usage=usage,
                finish_reason=getattr(raw.choices[0], "finish_reason", None) if raw.choices else None,
            )
        except Exception:
            raise AIProviderError(
                AI_ERROR_OUTPUT_INVALID, "The AI provider returned an invalid response."
            )


def get_provider() -> Optional[AIProvider]:
    """Return the configured provider or ``None`` (safe degraded mode)."""
    settings = get_settings()
    if settings.ai_provider == "openai":
        return OpenAIProvider()
    return None


def provider_supports(provider: Optional[AIProvider], capability: str) -> bool:
    return provider is not None and capability in provider.capabilities