# Vercel full-stack migration

Production: public [GitHub repository](https://github.com/justinchristroper-arch/helpdesk-ai) → one public Vercel Services deployment at [helpdesk-ai-mu-ten.vercel.app](https://helpdesk-ai-mu-ten.vercel.app/) → Neon PostgreSQL + pgvector. Hosted deterministic chat, citations, public browser flows and admin/auth acceptance passed; see [the verification record](vercel-migration-verification.md). Optional MindRouter synthesis is disabled and remains unverified in production. Render and Docker Hub are no longer production paths. Docker Compose remains a local development option.

## Official platform conventions checked 2026-09-28

- [Services](https://vercel.com/docs/services): available in beta on all plans; current `services` replaces `experimentalServices` for new projects.
- [Routing](https://vercel.com/docs/services/routing): rewrites select services and preserve the original request path.
- [Python](https://vercel.com/docs/functions/runtimes/python): standard uncompressed bundle limit is 500 MB. This project does not rely on Large Functions or a paid plan.
- [Request headers](https://vercel.com/docs/headers/request-headers): Vercel supplies the client IP. Only Vercel runtime requests use `x-vercel-forwarded-for`; arbitrary forwarding headers are ignored outside Vercel.

## Layout and behavior

Import the repository root (not `frontend`) into one Hobby project. Root `vercel.json` defines Vite in `frontend/` and FastAPI in `backend/`. `/api/*` routes to `backend/server.py`; that small entrypoint mounts the existing application at `/api`. Other paths route to Vite with SPA fallback. `/api/health`, `/api/docs` and `/api/openapi.json` are the public API diagnostics. Unknown API paths remain API 404s, not frontend HTML.

Production browser requests default to relative `/api`; leave `VITE_API_URL` unset. No wildcard CORS is necessary. Set `CORS_ORIGINS=[]` for the same-origin deployment. Local Docker endpoints retain their existing paths.

## Assets and build

Python 3.12 is selected by `backend/.python-version`. Runtime requirements flatten the existing lock's runtime pins, with pytest separated into `requirements-dev.txt`. The first hosted build rejected the nested constraints file before dependency installation. Backend build command: `python prepare_assets.py`. It downloads the same pinned quantized ONNX snapshot used in the Docker baseline, materializes one copy of the five runtime files, prepares tiktoken, and verifies a 384-dimensional embedding. The build requires public Hugging Face access but no API key, database connection, migration, bootstrap or LLM request.

Runtime uses the packaged model via FastEmbed's `specific_model_path`, `local_files_only=True`, and `HF_HUB_OFFLINE=1`. The small temporary cache directory is disposable. No user state is stored there. Model initialization is lazy and serialized; warm reuse is per instance, not a guarantee across requests. Each new instance still pays model import/loading cost. No model is downloaded in the browser or during a public request.

Initial Linux inventory: installed Python packages 313,360,162 bytes (including development packages); one model snapshot 67,179,163 bytes; tokenizer cache 1,681,126 bytes. Vercel's build reported a 302.27 MB pre-optimization bundle and a 108.17 MB deployed Python function on the first successful build. Hosted cold-start and runtime memory were not independently measured.

## Persistent state and database

Neon stores documents/extracted text, vectors, conversations, messages, source snapshots, feedback, generation reservations and request limits. Admin upload extracts bytes in memory and stores database records; original files are not retained. Large upload/reindex requests remain bounded by hosting request/time limits. The public demo primarily uses the existing synthetic corpus; only admins can mutate it.

Migration `0005` adds only `request_limits`, fixing the previous memory-only request limiter. Its sliding window uses database time and a per-identity transaction lock. Identities are hashed; expired counters are removed in bounded batches. Database errors fail closed with the API's safe storage error. Existing daily generation reservations remain unchanged at 3/user, 8/IP, 20/global; failed attempts count and each question permits at most one 300-token generation call.

Vercel defaults to SQLAlchemy NullPool, a 10-second connect timeout, and pre-ping. Connections close after each transaction/session; this avoids idle pools multiplied by function instances. Prefer a Neon pooled URL for greater concurrency, but preserve the validated direct URL initially rather than guessing a new host. Hobby concurrency is not a database capacity guarantee. Local Docker retains QueuePool 2+1. Never run migrations or seeding on function import. Apply migrations once before deployment using the existing private environment; do not reseed production.

## Server-only environment

Configure through Vercel secret environment settings, never frontend variables:

| Name | Value |
| --- | --- |
| `DATABASE_URL` | Existing Neon connection with SSL, kept secret |
| `JWT_SECRET` | New securely generated production value, at least 32 characters |
| `DATABASE_POOL_MODE` | `null` |
| `CORS_ORIGINS` | `[]` |
| `MINDROUTER_API_KEY` | Unset in the verified production baseline |
| `MINDROUTER_BASE_URL` | `https://api.mindrouter.io/v1` |
| `MINDROUTER_MODEL` | `openai/gpt-4.1-nano` |

Keep default generation caps (3/8/20, 300 tokens). Do not enable paid synthesis until explicitly authorized. The runtime entrypoint sets model/tokenizer paths, so no machine-specific cache path belongs in Vercel settings. `.vercelignore`, `.gitignore`, and function exclusions prevent local environments from being uploaded.

## Acceptance gate

Run full backend tests against an isolated/local database, frontend tests/lint/build, real Neon verification, secret/history scan, and diff checks before push. Hosted API acceptance covered health/docs, FastEmbed query retrieval, chunk-backed citations, history, feedback, unsupported fallback, ambiguity and follow-ups. The public browser loaded anonymous chat, a source panel, the document library, refresh/direct routes, and a 390 px mobile layout. The saved feedback indicator remained selected after refresh on the final application build. Hosted admin login and analytics returned HTTP 200 with real usage data; anonymous analytics returned 401, and guest analytics and document mutations returned 403. Temporary administrators were removed after acceptance. Hosted cold-start/memory measurement remains open.

This is a bounded synthetic portfolio demo, not an enterprise support service. Free quotas, platform beta behavior, cold starts, provider outages and connection limits apply. Do not enter confidential data. The GitHub repository and Vercel deployment are public; database and server credentials remain secret.
