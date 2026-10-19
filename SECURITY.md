# Security and operational boundaries

GraphPilot is a local developer tool, not an operating-system sandbox. Workspace path resolution blocks traversal, hidden paths and resolved symlinks outside the configured root. It cannot defend against a malicious local process swapping files concurrently. Run it with a dedicated task directory and normal user privileges.

Mutating tools require per-action human approval. Screen/file instructions do not grant authority; the system prompt explicitly treats them as untrusted. This reduces prompt-injection risk but does not prove a model will always interpret content correctly. Inspect proposed arguments, especially messaging, purchases or account changes.

The MCP companion has no independent approval UI; an MCP host must enforce its own authorization. Both repositories are designed for single-user local use. Neither should be exposed as an unauthenticated network service.

`.env`, workspace data, captures and SQLite state are excluded from source control. Keep secrets out of ordinary workspace files. Checkpoints can contain user prompts, tool output and images; they are not encrypted. Delete local state according to your own retention needs. Provider SDK logging is outside the application's full control; avoid debug logging and credential-bearing URLs. Raw provider exception bodies are not persisted by the graph.

Report a vulnerability privately through the repository owner's GitHub profile contact options; do not publish API keys or private captures in an issue.
