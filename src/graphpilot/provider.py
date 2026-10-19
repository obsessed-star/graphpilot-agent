"""Only this module knows how models are called. Tests inject a scripted provider."""

from __future__ import annotations

import os
from typing import Protocol

from graphpilot.config import Settings


class Provider(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> dict: ...


class ProviderError(RuntimeError):
    pass


class LiteLLMProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        import litellm

        litellm.suppress_debug_info = True
        options = {
            "model": self.settings.model,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "timeout": 45,
            "num_retries": 0,
        }
        if self.settings.model.startswith("groq/"):
            # Groq exposes the OpenAI chat protocol. LiteLLM 1.106.0's native
            # Groq response parser raises when optional service_tier is absent.
            # Use its public compatible transport, without patching SDK internals.
            options["model"] = "openai/" + self.settings.model.removeprefix("groq/")
            options["api_base"] = self.settings.api_base or "https://api.groq.com/openai/v1"
            variable = self.settings.api_key_env or "GROQ_API_KEY"
            key = os.getenv(variable)
            if not key:
                raise ProviderError(f"Missing key variable: {variable}")
            options["api_key"] = key
        if tools:
            options["tools"] = tools
            options["tool_choice"] = "auto"
        if self.settings.api_base:
            options["api_base"] = self.settings.api_base
        if self.settings.api_key_env:
            key = os.getenv(self.settings.api_key_env)
            if not key:
                raise ProviderError(f"Missing key variable: {self.settings.api_key_env}")
            options["api_key"] = key
        try:
            result = litellm.completion(**options)
        except Exception as exc:
            # Provider error text may echo request headers, prompts or credential-bearing URLs.
            status = getattr(exc, "status_code", None)
            reason = {401: "Authentication failed", 403: "Model access denied", 429: "Rate limit reached"}
            detail = reason.get(status, "Provider request failed; check model/tool support and configuration")
            raise ProviderError(f"{detail} ({type(exc).__name__}); automatic retries are disabled.") from None
        message = result.choices[0].message.model_dump(exclude_none=True)
        normalized = {k: message[k] for k in ("role", "content", "tool_calls") if k in message}
        normalized.setdefault("role", "assistant")
        normalized.setdefault("content", None)
        usage = result.usage.model_dump() if result.usage else {}
        return {"message": normalized, "usage": usage}
