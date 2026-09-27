# MindRouter HTTP 400 diagnosis — 2026-09-28

This diagnostic used one authenticated `GET /v1/models`, one minimal chat completion, and one final HelpDesk synthesis request after a locally tested correction. No repeated or binary-search API requests were made.

## Product request before correction

`POST https://api.mindrouter.io/v1/chat/completions` sent these JSON fields:

- `model`: `deepseek/deepseek-flash`
- `messages`: one short system instruction requesting fact-ID JSON and one user message containing a synthetic question plus approved fact IDs/text
- `max_tokens`: `300`
- `temperature`: `0`
- `response_format`: `{ "type": "json_object" }`

It did not send `stream`, JSON Schema, reasoning/thinking fields, tools, tool choice, DeepSeek-specific parameters, OpenRouter-specific parameters or any other extensions. The authorization header contained the ignored backend key and was never printed or stored in this report.

MindRouter documents all five submitted fields in its OpenAI-compatible chat API. The failure was nevertheless specific to provider-enforced JSON mode on this key/model route, as demonstrated below. The corrected product request omits `response_format` and retains strict local JSON/schema validation.

## Model and key restriction check

One authenticated model-catalog request returned HTTP 200 with exactly one available model ID: `deepseek/deepseek-flash`. It exactly matches the environment configuration. The effective catalogue for this key is therefore restricted to that single model, and the requested model is allowed.

MindRouter states that all models are normally available unless a per-key whitelist is set. To verify whether this single-model catalogue is intentional, inspect the current key under Dashboard → API Keys → edit key → model whitelist/allowed models. This restriction did not cause the HTTP 400 because both smoke and corrected HelpDesk requests reached the allowed model successfully.

## Minimal smoke request

The single minimal request contained only:

```json
{
  "model": "deepseek/deepseek-flash",
  "messages": [{"role": "user", "content": "Reply with OK."}],
  "max_tokens": 16
}
```

It returned HTTP 200. MindRouter reported model `deepseek-flash`, 34 input tokens, 14 output tokens, finish reason `stop`, and a nonempty two-character string. This proves the base URL, rotated key, allowed model and basic Chat Completions endpoint work.

## Isolated incompatibility and final request

Local reasoning eliminated the core fields proven by the smoke request. The system/user message format and `temperature: 0` are documented, and the synthetic input is far below the model context limit. `response_format` was the remaining per-model capability. The backend removed only that field; prompt-level JSON instructions and strict backend parsing remain.

One final HelpDesk request then returned HTTP 200, whereas the same HelpDesk path had returned HTTP 400 with `response_format`. This isolates the HTTP 400 incompatibility to `response_format: {"type":"json_object"}` for the active `deepseek/deepseek-flash` route.

The final response reported model `deepseek-flash`, 469 input tokens, 300 output tokens and finish reason `length`. Its `message.content` was an empty string; no `reasoning_content` field was present. The backend correctly rejected it as `content_not_fact_ids_json`, used the deterministic answer and returned two citations mapped to real PostgreSQL chunks. The 300-token ceiling was reached before visible JSON was returned, so real synthesis is still not fully verified. No further request was made.

## Request counts

- Model catalogue: one non-generation GET.
- Minimal smoke chat completion: one.
- Final corrected HelpDesk synthesis: one.
- Total external HTTP requests in this diagnostic: three, of which two were chat completions.

## Local verification after the correction

- Backend: 63 passed, with one existing Starlette/httpx deprecation warning.
- Frontend: four tests passed across two files.
- Lint: passed.
- Production build: passed.
- Alembic: revision `0004` at head; no new upgrade operations detected.
- Secret scan: 98 Git-visible files and three frontend bundle files checked; no potential secret files found.

[MindRouter chat documentation](https://mindrouter.io/en/docs/chat) documents the payload fields. [MindRouter error documentation](https://mindrouter.io/en/docs/errors) defines HTTP 400 `invalid_request` as request validation failure. [MindRouter FAQ](https://mindrouter.io/en/faq) describes per-key model whitelists.
