# HelpDesk AI

**Evidence-First IT Knowledge Assistant — Portfolio Project 4**

HelpDesk AI understands bounded natural-language IT questions using server-side FastEmbed, semantic intent examples, PostgreSQL/pgvector retrieval, deterministic response composition, and inspectable citations. Optional MindRouter synthesis can paraphrase approved source-backed facts for multi-source or long supported answers when a backend key and daily quota are available. Its live synthesis path has not yet passed validation; deterministic answers remain available.

Status: local retrieval and deterministic fallback verified. The final one-call GPT-4.1 Nano test returned HTTP 200 but failed sentence formatting; a conservative local correction is tested, with no further paid call. Real synthesis remains optional/unverified. See the [final pre-deployment report](docs/final-predeployment.md) and [verification history](docs/verification.md). Nothing is deployed or authorized for public publication.

## Why this architecture

For a bounded IT knowledge base, approved facts and procedures can be composed without external generation. Eligible answers may use one MindRouter request to rewrite relevant reviewed facts. The backend validates fact IDs and conservative structural grounding, then replaces internal IDs with citations from verified database rows. MindRouter use can incur charges and sends the question and approved facts to its service; leave the key unset to keep inference local. Hosting can also incur costs.

## How it works

1. Normalize the question and resolve limited follow-up context.
2. Embed on the server using cached BAAI/bge-small-en-v1.5 (384 dimensions).
3. Match persistent examples for 18 intents (180 positive queries, 54 contrastive/unsupported negatives).
4. Apply explainable similarity, scope, specificity, negative-example and ambiguity gates.
5. Retrieve at most three deduplicated pgvector evidence chunks from the mapped active documents.
6. Verify every approved factual sentence against its actual source text.
7. Compose steps, checklists, policies or SLA guidance with real source metadata. For multi-source answers or supported questions of at least 18 words with at least two facts, optionally ask MindRouter to rewrite approved facts marked with internal fact IDs. The backend validates markers, source coverage, unsupported values and evidence overlap, then renders public citations. Quota exhaustion, invalid output and provider failure retain the deterministic answer.

The FAQ path skips broader retrieval when the intent score is very high; it still queries and verifies authoritative evidence. Multi-source MFA/remote-work answers cite both documents. Unknown topics and undocumented details fall back; underspecified topics clarify.

## Local setup

Copy .env.example to .env and set a strong database password, matching DATABASE_URL and random JWT_SECRET. An optional MINDROUTER_API_KEY can be placed in ignored backend/.env; its URL and model are environment settings, with openai/gpt-4.1-nano as the default. Run docker compose up --build -d. For automated regression use `docker compose -f docker-compose.yml -f compose.offline.yml up --build -d` to disable paid synthesis even when a local key exists. First startup applies Alembic 0004, seeds eight bundled synthetic documents into an empty library, and indexes intent examples. Existing libraries are preserved.

Run npm ci and npm run dev inside frontend. Open http://localhost:5173 and ask a question immediately. Guest sessions are isolated and stored in sessionStorage. Use the existing management command for an admin account: docker compose exec api python -m app.manage create-user --email admin@example.test --role admin.

The Docker image downloads the embedding model and tokenizer at build time. Runtime FastEmbed uses local_files_only and HF_HUB_OFFLINE. The browser downloads only the web app, never the embedding model.

## Verification

- Backend: python -m pytest -q from backend; real seeded checks require LIVE_SEMANTIC=1 and TEST_DATABASE_URL.
- Frontend: npm test, npm run lint, npm run build. Production builds require VITE_API_URL set to an HTTPS backend origin; use a placeholder HTTPS origin for compile-only local checks, or the actual Render origin for deployment.
- Browser: npm run test:e2e with local API/frontend running and ignored .demo-credentials.json for the admin test.
- Real no-API fallback proof (explicitly clears the key): docker compose exec -T api python verify_offline.py.
- Evaluation: docker compose exec -T api python -m app.evaluate.

[Evaluation results](docs/evaluation-semantic.json) record all cases and definitions. The benchmark was inspected during development and is not an independent generalization estimate. Initial validation failures are preserved separately.

## Maintenance and trade-offs

See [dataset maintenance](docs/dataset-maintenance.md), [architecture](docs/design.md), [deployment](docs/deployment.md), [verification](docs/verification.md), and [case study](docs/case-study.md).

Semantic coverage depends on curated examples and approved fact mappings. Uploaded documents become searchable in the library, but answer coverage requires a reviewed intent mapping; arbitrary uploads do not silently become authoritative answer templates. English-focused, no OCR, no enterprise identity/retention workflow. Generation reservations persist in PostgreSQL across workers; the ordinary request limits remain process-local. Exact quotation proves source membership, not that the matcher understood every possible question.

Paraphrase grounding is a deterministic structural/lexical heuristic, not a guarantee of semantic correctness. Defaults are 3 generation attempts/user, 8/IP and 20 globally per UTC day, with at most one 300-token request per eligible question. Failed attempts count; there are no retries or answer-generation cache. Hosted proxy identity must be verified before claiming per-visitor IP behavior. The deployment target is Neon PostgreSQL, one Render Docker worker, and Vercel; [the runbook](docs/deployment.md) lists exact settings and pending hosted checks.

Historical citations remain snapshots after a source is removed. Synthetic policy corpus only; do not enter confidential data. Screenshots labelled local are local verification evidence, not deployed portfolio screenshots.
