# Validation record

Initial local validation: **19 October 2026**, Windows, Python 3.14.7.

| Check | Observed result |
|---|---|
| Agent tests with companion package installed | 23 passed |
| Ruff lint and formatting | Passed |
| Wheel and source distribution | Built successfully |
| Real graph offline CLI demo | Approval suspended before a write; resume produced the expected file; zero live calls |
| Persistent approval | SQLite checkpoint reopened in a new graph; approved operation executed |
| Cross-project integration | Real LangGraph graph and Phone controller exercised together over fake USB transport |
| Live Groq | Not tested; operator key not yet provided |
| Real USB phone | Not tested; device enumeration returned an empty list |

The model/provider is mocked in tests. The graph, registry, argument validation, checkpoint storage and phone controller are real code. No test uses a paid model request. The stdio protocol and image-content checks belong to the companion package's test suite.

Machine-readable check commands, local results and package hashes are in [validation.json](validation.json). Dependency versions are pinned in [requirements-dev.lock](../requirements-dev.lock). The source distribution hash records the local build at validation time; subsequent documentation commits can change a rebuilt source archive.

CI is configured for Windows/Linux and Python 3.11/3.14. Its live status is shown by the README badge; configuring a workflow alone is not evidence that all matrix jobs passed. No user credentials, prompts, serials or real screen captures are committed as evidence.

Before claiming a real phone workflow, connect a test device and run: observe → proposed operation → approval → action → inspect the new screen. Record a sanitized result and the exact tested model/device versions. Before claiming a new provider works, run an authorized live tool-calling task with that provider.
