# MindRouter parser revalidation — 2026-09-28

The key was rotated and stored only in ignored `backend/.env`. Before the run, the repository secret scanner found no matching local key in 94 Git-visible files or three frontend bundle files. `backend/.env.example` contains empty/configuration placeholders only.

Exactly two external requests were made with bundled synthetic HelpDesk AI data. Both were rejected by MindRouter with HTTP 400 before a chat completion was returned. The application therefore had no reported model, token usage, completion content, or completion schema to parse. It returned deterministic answers and backend citations in both cases. No additional paid request was made.

## Request 1 — MFA while working remotely

- MindRouter called: yes; external call 1 of 2.
- Requested model: `deepseek/deepseek-flash`; reported model: unavailable.
- HTTP status: **400**.
- Input/output tokens: unavailable.
- Model output validation: not reached; no completion was returned.
- Synthesis used: no. Deterministic fallback: yes.
- Citations: `[1]` mfa-reset-guide / “MFA stops working”; `[2]` remote-work-checklist / “Before remote work”. Both stored citations, excerpts and fact text map to their active retrieved PostgreSQL chunks.

Answer:

> Based on the current IT knowledge base:
>
> MFA stops working
> 1. Check that your phone has network access and automatic time enabled. [1]
> 2. If your authenticator is unavailable or your phone is lost, contact IT support and request an MFA reset. [1]
> 3. Support verifies identity through the registered employee recovery process before resetting enrollment. [1]
> 4. Do not approve unexpected sign-in prompts. [1]
>
> Before remote work
> 1. Use an approved managed laptop, install pending company updates, confirm MFA access, and test the VPN when internal services require it. [2]
> 2. Keep the service desk contact details accessible. [2]
> 3. Store work files only in approved company storage. [2]

## Request 2 — complex damaged-laptop paraphrase

- MindRouter called: yes; external call 2 of 2.
- Requested model: `deepseek/deepseek-flash`; reported model: unavailable.
- HTTP status: **400**.
- Input/output tokens: unavailable.
- Model output validation: not reached; no completion was returned.
- Synthesis used: no. Deterministic fallback: yes.
- Citation: `[1]` laptop-damage-procedure / “Immediate action”. Its stored citation, excerpt and fact text map to the active retrieved PostgreSQL chunk.

Answer:

> Here's the documented guidance:
>
> Immediate action
> 1. Stop using a damaged company laptop. [1]
> 2. For liquid spills or visible electrical damage, disconnect power if safe and do not switch the device back on. [1]
> 3. Report the incident to IT support with the asset tag, description, and photos if safe to obtain. [1]
> 4. Do not attempt repairs yourself. [1]

## Diagnosis and local fix

This run did not reproduce the earlier parser failure. It failed one stage earlier at the provider request boundary. The request still used the documented OpenAI-compatible fields: model, messages, `max_tokens`, temperature and JSON response format. Because the previous implementation discarded HTTP error bodies and this run was limited to two calls, the provider's specific error code could not be recovered after the processes exited. The exact reason for HTTP 400 is therefore unknown; it must not be described as a parser defect.

The backend now sanitizes future HTTP error responses into structural metadata only: root/error keys, error type/code, whether a message exists and its length. It does not retain error messages, response content, authorization headers or credentials. Unit tests cover this path and verify that private error text is excluded. The completion parser still records content/reasoning field types and lengths, validation reason and finish reason for successful HTTP responses. No third request was made to test the new diagnostics.

Real MindRouter synthesis is **not fully verified end to end**. HTTP transport worked in the previous run, but the earlier completions failed fact-ID validation and this revalidation received HTTP 400. Retrieval, deterministic fallback and backend-controlled citations remain verified.

## Final checks

- Backend: 63 passed; one existing Starlette/httpx deprecation warning.
- Frontend: four tests passed across two files.
- Lint and production build: passed.
- Migration check: no new upgrade operations detected; current migration remains 0004.
- Secret scan: 95 Git-visible files and three frontend bundle files scanned, zero potential secret files; six known local secret values were compared without printing them.
- Quota audit: the global counter increased from four to six, confirming exactly two reserved attempts in this run. The private environment file was absent from the built image.
