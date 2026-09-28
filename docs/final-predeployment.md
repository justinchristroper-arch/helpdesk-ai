# Final local pre-deployment report — 2026-09-28

Baseline: `935c12b`. This report belongs to the final local checkpoint; the actual commit hash is provided in the handoff and by `git log -1`. No push, public repository creation, deployment or hosted screenshot capture was performed.

## Readiness decision

**Ready for a controlled deterministic demo deployment with synthesis disabled.** Real hosted acceptance is still pending. **Real GPT-4.1 Nano synthesis is NOT verified end-to-end.** Exactly one paid call was made; its response was rejected, and a subsequent cosmetic parser correction was tested only offline. Public GitHub publication remains gated on hosted acceptance and explicit authorization.

## Final architecture and inventory

React/Vite → FastAPI → local FastEmbed `BAAI/bge-small-en-v1.5` (384 dimensions) → semantic intent matching and PostgreSQL/pgvector evidence retrieval → deterministic evidence gate/composer → optional MindRouter `openai/gpt-4.1-nano` paraphrase → backend-owned citations.

There are 18 reviewed intents, 180 positive examples (including canonical questions), 54 negative examples, eight synthetic documents and 25 source chunks. All 234 intent vectors and 25 source vectors have 384 dimensions. PostgreSQL is locally 17.11, pgvector 0.8.6, Alembic head/current `0004`; schema drift check passes. Inventory evidence is in [database-final.json](database-final.json). Usage/history counts are snapshots of local synthetic tests, not production activity.

Retrieval rules were not changed to improve model acceptance. PostgreSQL computes similarity; the evidence gate requires reviewed facts to occur in current source text. Missing/changed evidence rejects an answer. Ambiguous topics clarify; unsupported questions return the deterministic insufficient-evidence message without generation. Context handling remains limited to reviewed topic follow-ups. Uploads appear in the document library, but new answer coverage requires reviewed intent mappings.

## Exactly one real synthesis call

Question: “My MFA is broken while I'm working remotely. What should I do?”

| Field | Measured result |
|---|---|
| External generation calls in this pass | **1** |
| HTTP status | 200 |
| Requested model | `openai/gpt-4.1-nano` |
| Reported model | `gpt-4.1-nano-2025-04-14` |
| Input / output tokens | 246 / 57 |
| Reasoning tokens | 0 |
| Finish reason | `stop` |
| Visible content length | 293 characters |
| Fact IDs accepted before failure | None (`[]`) |
| Validation | Rejected: `malformed_sentence` |
| Synthesis displayed | No |
| Deterministic fallback | Yes |
| Public citation 1 | `mfa-reset-guide`, “MFA stops working” |
| Public citation 2 | `remote-work-checklist`, “Before remote work” |
| Citation → active PostgreSQL chunk checks | Both passed |

Full safe results, chunk IDs and the actual fallback answer: [validation-final-nano.json](validation-final-nano.json). The returned source answer includes phone connectivity/time checks, requesting an MFA reset, identity verification, rejecting unexpected prompts, managed laptop/update/MFA/VPN requirements, service desk contact availability and approved storage—all from synthetic documents.

The captured structure showed separately marked sentences on one physical line. The original validator rejected the whole line because it contained interior markers/multiple sentences. After the call, normalization was extended to split only after complete marker groups. Synthetic fixtures matching the captured punctuation pattern pass locally. The rejected original prose was not retained, so neither exact-response replay nor live acceptance of that correction is claimed. No second paid call was made.

## Validator and cost controls

Accepted harmless grammar: single/grouped/adjacent IDs, comma-separated markers, bold/parenthesis wrappers, trailing punctuation, bullet/number prefixes and separately marked inline sentences. The parser rejects malformed/unknown/duplicate IDs and unbalanced wrappers. Every factual segment needs valid IDs; uncited sentences are not covered by a nearby marker.

Validation checks each cited fact's lexical relationship, all required source coverage, unsupported structured values, sensitive policy/procedure terms, conservative named-entity checks, negation, Unicode controls, output length and active database evidence. It rejects token-truncated responses. Internal IDs become backend public citation numbers; the model never supplies document metadata. These are conservative deterministic heuristics, **not semantic entailment guarantees or a hallucination-free claim**.

Daily defaults remain 3 attempts/user, 8/IP and 20 globally, counted by UTC date in PostgreSQL before the request under an advisory transaction lock. Failed attempts count. One eligible question makes at most one external request, with at most 300 output tokens. All limits remain environment-configurable. Missing key, exhausted quota/storage, timeout, invalid schema/content and provider errors preserve deterministic answers. No retries, agent loops, reranking, external embeddings or answer-generation cache were added.

## Changes from baseline

- Expanded marker grammar, safer inline segmentation, stronger adversarial tests and stop-only completion acceptance.
- Malformed provider JSON/message shapes fail closed; safe structural metadata aids local diagnosis without storing rejected prose or reasoning.
- Default model is GPT-4.1 Nano; requests contain only `model`, `messages`, `max_tokens`.
- Removed obsolete multi-call/provider diagnostic scripts and Railway runtime config; retained historical verification documents. The guarded single-call script remains for a separately authorized future validation.
- Lazy model initialization is locked; embeddings serialize with batches of eight; worker count is explicitly one. DB pool is 2+1; quota queries read only the three relevant rows, and intent maintenance reads IDs rather than vectors.
- Analytics splits deterministic/synthesized answers using stored generation state and aggregates feedback in SQL. Public messages expose safe status only.
- Frontend handles cold starts/network failure without automatic retry, explains quota fallback, avoids a production localhost fallback, and rejects invalid production API origins during build.
- Added key-disabled regression overlay, Render readiness template, resource proof, deployment runbook and portfolio material. Bootstrap admin email normalization matches login.

## Verification evidence

Backend: **163 tests passed, none skipped**, including real PostgreSQL/pgvector tests, in the final full run. Frontend: **6 tests passed**. Lint and production build pass; output JS is approximately 285.8 kB / 90.1 kB gzip. Production compilation used an HTTPS placeholder API origin, not a deployed endpoint.

Browser: **5 real Edge scenarios passed**, plus an agent-browser visual check without browser errors. Coverage includes anonymous supported/paraphrased VPN, successful “it” follow-up, MFA/remote multi-source, laptop damage, software installation, database access, account unlock, incident SLA, unsupported input, clarification choices, citations, feedback, persisted history/refresh, public library, mobile source panel, direct routes, admin upload/reindex/removal and analytics. Provider disabled is exercised against the actual local API. Quota/failure/timeout/synthesis states are tested with controlled local provider boundaries; no extra paid requests are hidden in browser testing.

The no-key integration flow passed with **zero non-database socket attempts** in 25.791 seconds under 512 MB / 0.1 CPU: [offline-final.json](offline-final.json). Operational Python syntax checks pass. Secret scanning covers Git-visible files, built frontend assets, known local values and token patterns in reachable Git history. No matches were found; `backend/.env` is ignored, examples contain placeholders, and `/app/.env` is absent from the image. This is a scoped secret scan, not a security certification.

### Measured synthetic evaluation

All 80 cases are inspected regression cases, not an independent benchmark. [Full measured output and definitions](evaluation-final.json):

| Metric | Result |
|---|---|
| Intent Top-1 / Top-3 | 53/53 each |
| Supported answer recall | 53/53 |
| Returned evidence Hit@3 | 53/53 |
| Citation-to-chunk validity | 53/53 answered cases |
| Verbatim fact support | 53/53 answered cases |
| Unsupported rejection | 21/21 |
| Ambiguity handling | 6/6 |
| Follow-up resolution | 6/6 |

Verbatim support measures exact source membership for deterministic answers. It is not a measured semantic support rate for model paraphrases. The earlier initial-validation failures remain preserved; no scores were invented.

### Resource and warning classification

Under the actual 512 MB / 0.1 CPU local Docker limit, 25 sequential retrieval queries completed in 31.2 seconds. Observed process RSS stabilized around 317.05–317.38 MiB from query 5 through 25; all cgroup OOM counters were zero. See [resource-final.json](resource-final.json). This is a bounded sample, not proof of leak freedom, load capacity, hosted latency or concurrency readiness.

- Nonblocking dependency debt: Starlette's test client warns that its httpx adapter is deprecated in favor of httpx2. Tests pass; this is test infrastructure, not a runtime provider failure. No broad dependency migration was introduced.
- Harmless environment warnings: Node FORCE_COLOR overrides NO_COLOR; Windows Git reports LF/CRLF conversion. Final whitespace check passes.
- Resolved local prerequisite: Docker Desktop's Linux engine was stopped. Starting it restored the stack without volume deletion. The older dockerInference-socket incident's underlying cause remains historically unproven.
- Deployment limitations: free-tier cold starts, actual Neon TLS/migrations, platform proxy identity, hosted memory and CORS still require hosted acceptance. Do not interpret local checks as those results.

## Deployment and publication handoff

The [deployment runbook](deployment.md) contains exact Neon, Render and Vercel environment examples, build/start commands, health route, TLS, CORS and acceptance steps. Required backend secrets/settings: `DATABASE_URL` in psycopg format with SSL, random `JWT_SECRET`, exact JSON `CORS_ORIGINS`. Optional `MINDROUTER_API_KEY` remains empty initially; model/base URL/300-token cap/3-8-20 quotas are listed explicitly. `VITE_API_URL` is the only frontend variable; it must be the actual HTTPS backend origin.

Next authorized phase: create Neon; deploy one Render worker with synthesis disabled; verify storage/bootstrap/health; deploy Vercel; configure exact CORS; run hosted E2E, proxy identity and resource checks; capture deployed screenshots; then separately approve public publication. A private Git push or registry image may be needed for Render's build source and requires authorization. No public push is needed to validate hosting.

Portfolio description, business AS-IS/TO-BE, architecture decisions, CV bullets and interview points are in [case-study.md](case-study.md). Local desktop/mobile images in `screenshots/` are labelled local, never presented as hosted evidence.

There is no known blocker to the tested deterministic demo path. Optional live synthesis remains unverified, and the hosted/public completion gates are deliberately still open.
