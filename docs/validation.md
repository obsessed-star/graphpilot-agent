# Validation record

Latest local validation: **20 October 2026**, Windows, Python 3.14.7. Initial checks were performed on 19 October.

| Check | Observed result |
|---|---|
| Agent and companion tests together | See current count and commands in [validation.json](validation.json) |
| Ruff lint and formatting | Passed |
| Wheel and source distribution | Built successfully |
| Real graph offline CLI demo | Approval suspended before a write; resume produced the expected file; zero live calls |
| Persistent approval | SQLite checkpoint reopened in a new graph; approved operation executed |
| Cross-project integration | Real LangGraph graph and Phone controller exercised together over fake USB transport |
| Actual LiteLLM HTTP boundary | Real CLI processes complete approval/denial and SQLite resume against a local scripted HTTP server |
| HTTP 401 and 429 | One request per failure, no retries, process exits with status 2 |
| Live Groq | Verified with `openai/gpt-oss-20b`: three requests, approval pause, SQLite resume, exact file write and read-back |
| Real USB phone | Not tested; device enumeration returned an empty list |

Most unit tests inject a scripted provider. The HTTP integration tests also run the real LiteLLM adapter and CLI over loopback HTTP, with scripted model responses. The graph, registry, argument validation, checkpoint storage and phone controller are real code. No test uses a paid model request or demonstrates actual model reasoning. The stdio protocol and image-content checks belong to the companion package's test suite.

## Defects found by the deeper HTTP check

The initial 0.1.0 unit suite did not exercise the installed SDKs together over HTTP. LiteLLM 1.106.0's native Groq parser failed when optional `service_tier` metadata was absent; its tool pipeline also required MCP 2 types when an incompatible MCP 1 installation was present. Version 0.1.1 uses Groq's public OpenAI-compatible transport, explicitly depends on a compatible MCP SDK, and verifies the actual HTTP boundary. The CLI also now exits unsuccessfully for provider/budget failures instead of reporting shell success after a failed task. Use 0.1.1 or newer rather than the initial preview.

Machine-readable check commands, local results and package hashes are in [validation.json](validation.json). Dependency versions are pinned in [requirements-dev.lock](../requirements-dev.lock). The source distribution hash records the local build at validation time; subsequent documentation commits can change a rebuilt source archive.

CI is configured for Windows/Linux and Python 3.11/3.14. Its live status is shown by the README badge; configuring a workflow alone is not evidence that all matrix jobs passed. No user credentials, prompts, serials or real screen captures are committed as evidence.

Before claiming a real phone workflow, connect a test device and run: observe → proposed operation → approval → action → inspect the new screen. Record a sanitized result and the exact tested model/device versions. Before claiming a new provider works, run an authorized live tool-calling task with that provider.

## Live verification after 0.1.1

On 20 October, the configured Llama model was absent from the provided key's Groq model list. The live test selected the available `openai/gpt-oss-20b`. A 256-token probe consumed its budget on reasoning and returned no visible output, revealing that `finish_reason` had been discarded and an empty reply was falsely considered completed. Version 0.1.2 preserves finish reasons, stops truncated/empty replies as failures, and uses the verified model by default.

With an explicit 1,024-token output budget, the actual Groq-backed graph paused before writing, resumed from a reopened SQLite checkpoint, wrote the exact synthetic marker and read it back using a registered tool. The successful run used 2,124 total tokens across three requests. [Sanitized evidence](live-groq-2026-10-20.json) records provider-reported usage and independent file checks; it contains no key, account identifier or private input. The key was used only in the transient test process and not retained. This does not establish real-phone behavior or live compatibility for other providers.
