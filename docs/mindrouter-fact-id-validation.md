# MindRouter fact-ID grounding validation — 2026-09-28

The synthesis contract was redesigned to permit natural paraphrases without giving the model control over citations or source metadata. The backend assigns `F#` identifiers to approved facts, retaining each fact's source document, chunk, section, excerpt and public citation number. Only the IDs and fact text are sent to MindRouter.

## Deterministic validation

Before accepting model content, the backend checks that every nonempty line is one factual sentence ending in valid fact IDs, every retrieved source is represented, internal markers are well formed, and cited evidence still belongs to active PostgreSQL chunks. It rejects unsupported numbers, URLs, email addresses, phone numbers and policy-specific terms, weak deterministic lexical overlap, duplicate or unknown IDs, excessive output and malformed content. Accepted `F#` markers are replaced with public citation numbers. No second LLM is used, and rejected text is never shown to the user.

Local tests cover exact approved wording, legitimate paraphrases, multi-fact sentences, unknown IDs, missing IDs, invented SLA numbers, invented approval requirements, invented contact data, malformed markers, multiple sentences behind one marker, empty or excessive output, citation conversion, inactive evidence and deterministic fallback. The complete backend suite passed 74 tests before the real call.

## Single real validation

Exactly one request was made for `My MFA is broken while I'm working remotely. What should I do?` using `openai/gpt-4.1-nano`.

- HTTP status: `200`
- requested model: `openai/gpt-4.1-nano`
- reported model: `gpt-4.1-nano-2025-04-14`
- input tokens: `232`
- output tokens: `62`
- reasoning tokens: `0`
- finish reason: `stop`
- visible content length: `331` characters
- recognized fact IDs before failure: none
- validation: failed with `malformed_fact_marker`
- synthesis shown: no
- deterministic fallback: yes
- external generation calls: one

The safe diagnostic did not retain rejected content. It can therefore establish only that the first nonempty generated line contained brackets but did not end in the accepted `[F1]` or `[F2,F3]` grammar. Possible formatting differences such as trailing punctuation, Markdown wrappers or adjacent marker groups cannot be distinguished from the retained metadata. No second paid request was made and the marker grammar was not weakened speculatively.

The final public response was the existing deterministic multi-source MFA and remote-work answer. Its two backend citations mapped to current PostgreSQL evidence:

1. `mfa-reset-guide`, section `MFA stops working`, chunk `276210ed-75c0-4f45-bfd2-32c95885d71d`.
2. `remote-work-checklist`, section `Before remote work`, chunk `85a3d73d-7a00-4908-8ac0-aac482f234b8`.

Post-request verification passed: 74 backend tests, four frontend tests, lint, production build, Alembic revision `0004` at head with no new upgrade operations, and the secret scan. GPT-4.1 Nano synthesis is not yet verified end to end.
