# Model providers

GraphPilot uses [LiteLLM's completion interface](https://docs.litellm.ai/docs/) and accepts its `provider/model` identifiers. It does not claim every model supports tools or images. Choose a tool-capable chat model; enable vision only for a model that supports image input and tool use in the same conversation.

| Provider | Example `AGENT_MODEL` | Key variable | Notes |
|---|---|---|---|
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` | Initial text/tool configuration; uses the Android UI tree |
| Anthropic | `anthropic/<available-model>` | `ANTHROPIC_API_KEY` | Select an accessible tool-capable model |
| Gemini | `gemini/<available-model>` | `GEMINI_API_KEY` | Model availability depends on your account |
| OpenAI | `openai/<available-model>` | `OPENAI_API_KEY` | Set an actual accessible model ID |
| Ollama | `ollama_chat/<local-model>` | Usually none | Set `AGENT_API_BASE=http://localhost:11434`; model must support tools |
| OpenAI-compatible endpoint | `openai/<your-model>` | Your variable | Set `AGENT_API_BASE` and `AGENT_API_KEY_ENV` |

Provider examples are configuration routes, not evidence of live compatibility testing. The adapter forwarding contract is tested offline. Other LiteLLM providers can be selected the same way, subject to their credentials, optional SDKs and model capabilities.

Groq uses LiteLLM's OpenAI-compatible transport with the Groq endpoint and `GROQ_API_KEY`; the request still goes to Groq, not OpenAI. This avoids a response-parsing regression in LiteLLM 1.106.0. The Groq model prefix and configuration remain unchanged for users. Local HTTP tests cover this actual transport, approval/resume, and 401/429 errors. Other providers retain their native LiteLLM adapters. MCP 2.3+ is constrained compatibly across the agent and companion tool.

## Custom gateway

```dotenv
AGENT_MODEL=openai/my-tool-capable-model
AGENT_API_BASE=https://your-gateway.example/v1
AGENT_API_KEY_ENV=MY_GATEWAY_KEY
AGENT_VISION=false
```

Save the key privately with `python -m graphpilot.cli configure --key-env MY_GATEWAY_KEY`. Do not put credentials in an API URL. The default `.env` file is ignored by Git. No key is embedded in the repository or needed for CI.

## Groq and vision

The default model is a text model. It sees UI element labels, bounds and centers, rather than screenshot pixels. Screenshot files are still captured locally. To use visual reasoning, select a currently available [Groq vision model](https://console.groq.com/docs/models) and set `AGENT_VISION=true`. Do not assume any listed model remains available indefinitely. Unsupported tool/image combinations fail explicitly; the agent does not silently fall back to a paid model.

Screen contents are transmitted to your chosen provider when its tool results are used; vision mode also transmits the latest screenshot. Use a test device and non-sensitive screens for a public demo. Actual phone captures and session databases stay ignored locally.
