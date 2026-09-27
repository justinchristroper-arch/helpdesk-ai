# MindRouter GLM validation — 2026-09-28

The configured backend-only key was allowed to use `zai/glm-5.3-flash`. Before the request, `backend/.env` was confirmed ignored, the effective model was confirmed without printing the key, and the secret scan found no local key in tracked files or the frontend production bundles.

## Request

Exactly one generation request was made for the synthetic multi-source question: `My MFA is broken while I'm working remotely. What should I do?`

The JSON payload contained only:

- `model`: `zai/glm-5.3-flash`
- `messages`: a concise instruction plus the question, approved facts and backend-issued source markers
- `max_tokens`: `300`

It did not contain temperature, `response_format`, thinking/reasoning parameters, tools, tool choice or provider-specific extensions. FastEmbed, pgvector retrieval, the semantic evidence gate, persisted quotas and deterministic fallback ran through the normal backend path.

## Result

- external generation calls: `1`
- HTTP status: `200`
- requested model: `zai/glm-5.3-flash`
- reported model: `glm-5.3-flash`
- input tokens: `207`
- output tokens: `300`
- reasoning tokens: `298`
- finish reason: `length`
- visible content length: `0`
- validation: failed with `content_not_approved_facts`
- synthesis shown: no
- deterministic fallback: yes

The sanitized response contained a normal choice and message object, but `message.content` was an empty string and no `reasoning_content` field was returned. The usage breakdown nevertheless reported 298 reasoning tokens. With no reasoning controls in the request, the MindRouter GLM route used nearly the full 300-token completion budget before producing visible content. No second request was made.

The fallback returned two backend-controlled citations, both verified against current PostgreSQL data:

1. `mfa-reset-guide`, section `MFA stops working`, chunk `276210ed-75c0-4f45-bfd2-32c95885d71d`.
2. `remote-work-checklist`, section `Before remote work`, chunk `85a3d73d-7a00-4908-8ac0-aac482f234b8`.

Post-request verification passed: 63 backend tests, four frontend tests, lint, production build, Alembic revision `0004` at head with no new upgrade operations, and the secret scan. Real MindRouter synthesis is not yet verified end to end.
