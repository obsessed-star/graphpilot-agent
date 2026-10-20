from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model: str = "groq/openai/gpt-oss-20b"
    api_base: str | None = None
    api_key_env: str | None = None
    vision: bool = False
    max_model_calls: int = 8
    max_tool_calls: int = 12
    max_tokens: int = 1024
    max_input_chars: int = 24000

    def __post_init__(self):
        for name in ("max_model_calls", "max_tool_calls", "max_tokens", "max_input_chars"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

    @classmethod
    def from_env(cls):
        return cls(
            model=os.getenv("AGENT_MODEL", cls.model),
            api_base=os.getenv("AGENT_API_BASE") or None,
            api_key_env=os.getenv("AGENT_API_KEY_ENV") or None,
            vision=os.getenv("AGENT_VISION", "false").lower() == "true",
            max_model_calls=int(os.getenv("AGENT_MAX_MODEL_CALLS", "8")),
            max_tool_calls=int(os.getenv("AGENT_MAX_TOOL_CALLS", "12")),
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "1024")),
            max_input_chars=int(os.getenv("AGENT_MAX_INPUT_CHARS", "24000")),
        )
