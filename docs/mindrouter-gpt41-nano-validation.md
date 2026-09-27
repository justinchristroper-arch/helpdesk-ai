# MindRouter GPT-4.1 Nano validation — 2026-09-28

The backend-only key was configured for `openai/gpt-4.1-nano`. Before the request, `backend/.env` was confirmed ignored, the effective model was verified without printing the key, and the secret scan found no key in tracked files or frontend bundles.

## Request

Exactly one generation request was made through the normal HelpDesk chat path for: `My MFA is broken while I'm working remotely. What should I do?`

The JSON payload contained only:

- `model`: `openai/gpt-4.1-nano`
- `messages`: the concise grounding instruction plus the question, approved facts and backend-issued source markers
- `max_tokens`: `300`

It contained no temperature, `response_format`, thinking/reasoning parameters, tools, tool choice or provider-specific extensions. FastEmbed, pgvector retrieval, the semantic evidence gate, persisted quotas and deterministic fallback remained unchanged.

## Result

- external generation calls: `1`
- HTTP status: `200`
- requested model: `openai/gpt-4.1-nano`
- reported model: `gpt-4.1-nano-2025-04-14`
- input tokens: `201`
- output tokens: `55`
- reasoning tokens: `0`
- finish reason: `stop`
- visible content length: `289` characters
- validation: failed with `content_not_approved_facts`
- synthesis shown: no
- deterministic fallback: yes

GPT-4.1 Nano returned a normal, nonempty visible completion without spending tokens on reasoning, resolving the previous reasoning-budget limitation. The backend deliberately retains no model text after validation failure. The sanitized metadata therefore establishes that the completion differed from the required complete, verbatim approved-fact lines, but cannot safely distinguish paraphrasing, formatting differences or missing source coverage. The validator was not loosened and no second request was made.

The fallback returned two backend-controlled citations, both verified against current PostgreSQL rows:

1. `mfa-reset-guide`, section `MFA stops working`, chunk `276210ed-75c0-4f45-bfd2-32c95885d71d`.
2. `remote-work-checklist`, section `Before remote work`, chunk `85a3d73d-7a00-4908-8ac0-aac482f234b8`.

Post-request verification passed: 63 backend tests, four frontend tests, lint, production build, Alembic revision `0004` at head with no new upgrade operations, and the secret scan. Real MindRouter synthesis is not yet verified end to end.
