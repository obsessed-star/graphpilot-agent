# Phone goal feature validation — 2026-10-20

GraphPilot 0.2.0 and USBPhone Control 0.2.0.

- Combined source suite: **89 passed in 82.60 seconds**, Python 3.14 on Windows.
- Ruff lint, format and Git whitespace checks passed in both repositories.
- Both source distributions and wheels built successfully using isolated Hatchling environments.
- Three new cross-repository workflow fixtures cover application confirmation, refusal before final
  submission, and document download/export with exact bytes and SHA-256 comparison.
- Phone tests also cover HTTP(S) intents, Android intent errors, invalid schemes, filename traversal,
  symlinks, empty/oversized files and checksum mismatch.

The workflow provider and USB transport are deterministic fixtures. They do not place a real call,
submit an actual application, issue an official document or test live model planning. No new paid model
requests were made for this feature. `adb devices -l` returned no connected devices during validation.
The earlier live Groq workspace test remains separate evidence; it does not validate these phone flows.

Pending: physical Android validation, representative real sites, Unicode keyboard input, upload from PC
workspace to phone, and outcome evaluation with a live model. CLI completion status is model termination,
not independent goal certification. See [task flows and limits](phone-goals.md).
