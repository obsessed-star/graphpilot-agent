# Give the goal, not the taps

GraphPilot receives the desired outcome. The model chooses applications and UI steps from the current
phone observation; the user does not have to prescribe "open Chrome, tap here, then type this".
The separate USBPhone repository provides actions, not an AI planner or fixed site-specific script.

```powershell
python -m graphpilot.cli run "Bu iş ilanına benim için başvur: https://example.org/jobs/123. Bilgilerimi workspace dosyalarından oku." --phone --session application
python -m graphpilot.cli run "https://example.org/portal adresinden öğrenci belgemi indir ve kaydedilen dosyayı ver." --phone --session document
```

These are templates: substitute the actual employer/site. They are not supported-site promises.
Install USBPhone Control 0.2.0+ into the same environment. For longer tasks, choose explicit budgets
before starting (for example `AGENT_MAX_MODEL_CALLS=30`, `AGENT_MAX_TOOL_CALLS=30`,
`AGENT_MAX_INPUT_CHARS=96000`). Larger budgets can cost more; they do not guarantee completion.
The default eight model requests intentionally limit spending on short tasks.

## Application flow

1. Observe the phone and open the supplied vacancy URL using `phone_open_url`.
2. Inspect the vacancy and form. Read existing user documents from the bounded workspace.
3. Fill verified facts and use the phone's file picker for existing attachments. A PC workspace file
   is not automatically on the phone; this version has no upload/push tool.
4. Ask for necessary missing facts rather than fabricate answers. Host approval remains required for
   each phone action, including submission; approval chooses whether to execute, not the next UI step.
5. Read the result for a receipt/reference or explicit confirmation. A click or new screenshot alone
   does not demonstrate acceptance. Never blindly retry a final submission.

## Document flow

1. List Downloads before navigating, so an old file is not mistaken for new evidence.
2. Open the portal, inspect each screen and request the intended document.
3. Inspect the download/viewer state and Downloads again. Resolve duplicate or replaced names from
   the actual UI; do not infer a new download merely from filename presence.
4. `phone_export_download` copies a named regular file from `/sdcard/Download` into local capture
   storage. It rejects empty files, files above 20 MiB, paths, symlinks and changing bytes.
5. Report path, size and SHA-256. `transfer_verified` compares device and copied bytes;
   `content_verified=false` leaves document identity/authenticity unproven. Inspect the document in
   the phone viewer for its title and identity before making content claims.

Android uses [VIEW intents for web URLs](https://developer.android.com/guide/components/intents-common#Browser).
The transport uses [ADB shell operations](https://developer.android.com/tools/adb) on the selected USB
device, with separately quoted arguments. No desktop browser session is involved.

## Practical limits and verification

OTP, CAPTCHA, locked/secure screens and unavailable personal facts require user participation.
Stock ADB typing supports printable ASCII without `%`; Turkish Unicode form input is not implemented.
The agent must report this limitation instead of altering a person's name or answer.
Some sites expose little accessibility text; use a suitable vision model when necessary.
The default Groq model is text-only and cannot interpret screenshots as vision input.

`tests/test_phone_goals.py` runs the actual graph, approval/resume flow, registry and Phone controller
over a synthetic USB transport. Three fixtures cover application confirmation, denied submission and
a new downloaded file exported with an exact hash. The provider is deterministic: these tests do not
validate live AI planning, an actual application, an issued document, or physical hardware.
Live end-to-end phone validation remains pending a connected, authorized Android device.

CLI `status=completed` means the model ended its turn, not independent certification of goal success.
Assess the reported evidence and unresolved limitations.

[Feature validation record](phone-goals-validation.md)
