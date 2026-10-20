# Changelog

## 0.2.0 — 2026-10-20

- Treat phone requests as user outcomes: application submission, document retrieval and contact calls.
- Add phone URL navigation, public Downloads listing and byte-verified file export tools.
- Define missing-information, unexpected-screen and final-outcome evidence behavior in the agent policy.
- Add real graph/controller integration fixtures for application confirmation, denied submission and document export.
- These fixtures test orchestration, not live model planning or compatibility with every website/device.

## 0.1.2 — 2026-10-20

- Verify the actual Groq service: approval, SQLite resume, file write and read-back completed in three model requests and two tools with `openai/gpt-oss-20b`.
- Update the default model to the live-verified model; the prior default was not listed for the test credential.
- Preserve provider finish reasons. Token-truncated reasoning responses now stop as `output_limit` instead of false completion, without executing partial tool calls.
- Reject empty visible responses as `empty_response`; both failure states return CLI exit status 2.
- Add unit and real-HTTP regression coverage; no credential is persisted or included in evidence.

## 0.1.1 — 2026-10-20

- Exercise the real CLI/LiteLLM HTTP boundary for approval, denial, persistence, authentication and rate-limit failures.
- Use Groq's public compatible transport to avoid the native LiteLLM 1.106.0 parser regression on optional metadata.
- Require the compatible MCP 2.3 SDK across the two projects instead of installing incompatible MCP 1 types.
- Return exit status 2 when model execution fails or a budget terminates the task; preserve sanitized diagnostics.

## 0.1.0 — 2026-10-19

Initial local preview with a unit-tested graph, durable approval and a separate USB transport. Superseded by 0.1.1 after deeper HTTP integration checks found runtime defects.
