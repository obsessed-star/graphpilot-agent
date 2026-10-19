# Changelog

## 0.1.1 — 2026-10-20

- Exercise the real CLI/LiteLLM HTTP boundary for approval, denial, persistence, authentication and rate-limit failures.
- Use Groq's public compatible transport to avoid the native LiteLLM 1.106.0 parser regression on optional metadata.
- Require the compatible MCP 2.3 SDK across the two projects instead of installing incompatible MCP 1 types.
- Return exit status 2 when model execution fails or a budget terminates the task; preserve sanitized diagnostics.

## 0.1.0 — 2026-10-19

Initial local preview with a unit-tested graph, durable approval and a separate USB transport. Superseded by 0.1.1 after deeper HTTP integration checks found runtime defects.
