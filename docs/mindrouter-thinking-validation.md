# MindRouter non-thinking validation — 2026-09-28

## Previously captured response

The prior corrected HelpDesk request stored only sanitized metadata:

- HTTP status: `200`
- requested model: `deepseek/deepseek-flash`
- reported model: `deepseek-flash`
- input tokens: `469`
- completion tokens: `300`
- finish reason: `length`
- visible content type: string
- visible content length: `0`
- `reasoning_content` field present: no
- reasoning-token count: not captured by that response diagnostic

The response therefore suggested that thinking consumed the budget, but did not prove it.

## Local request correction

DeepSeek's current Chat Completions documentation states that thinking defaults to enabled and documents `thinking: {"type":"disabled"}` for non-thinking mode. MindRouter documents an OpenAI-compatible endpoint and normalized DeepSeek responses, but its thinking page does not document this DeepSeek switch. The request used the upstream-compatible switch because it was the only documented DeepSeek toggle; no undocumented alternative was guessed.

The product request was reduced to four top-level fields:

- `model`: `deepseek/deepseek-flash`
- `messages`: one short grounding instruction and one user message containing only the question, approved facts and source markers
- `max_tokens`: `300`
- `thinking`: `{ "type": "disabled" }`

It omitted temperature, response format, tools, reasoning effort, conversation history, retrieval scores, document metadata and provider extensions. Strict local tests require the model to return complete, verbatim approved facts with backend-issued markers and at least one fact from every retrieved source. The backend remains responsible for the displayed citation mapping.

## Single real validation request

Exactly one external chat-completion request was made using the synthetic multi-source question: `My MFA is broken while I'm working remotely. What should I do?`

- HTTP status: `200`
- requested model: `deepseek/deepseek-flash`
- reported model: `deepseek-flash`
- input tokens: `226`
- completion tokens: `300`
- reported reasoning tokens: `300`
- finish reason: `length`
- visible content length: `0`
- `reasoning_content` field present: no
- validation: failed with `content_not_approved_facts`
- synthesis shown: no
- deterministic fallback: yes
- external calls: one

The response proves that every completion token was billed/reported as reasoning even though the request included `thinking: {"type":"disabled"}`. The active MindRouter route accepted the field but did not honor it for `deepseek/deepseek-flash`. No second request was made. MindRouter documents `reasoning_effort` for OpenAI o-series models with `low`, `medium` and `high`; it does not document the upstream DeepSeek `none` value. Replacing the field with `reasoning_effort: "none"` would therefore be an unverified guess and was not attempted.

The fallback returned two citations, both verified against their current PostgreSQL chunks:

1. `mfa-reset-guide`, section `MFA stops working`, chunk `276210ed-75c0-4f45-bfd2-32c95885d71d`.
2. `remote-work-checklist`, section `Before remote work`, chunk `85a3d73d-7a00-4908-8ac0-aac482f234b8`.

Local verification before the real request passed: 63 backend tests, four frontend tests, lint, production build, Alembic revision `0004` at head with no new upgrade operations, and the secret scan.

[MindRouter chat completions](https://mindrouter.io/en/docs/chat) documents the gateway request fields. [MindRouter reasoning/thinking](https://mindrouter.io/en/docs/thinking) describes its published reasoning controls. [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/) documents the upstream non-thinking switch and usage metadata.
