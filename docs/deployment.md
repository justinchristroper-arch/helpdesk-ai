# Neon / Render / Vercel deployment runbook

Prepared locally on 2026-09-28. The Neon database is provisioned and verified; Render and Vercel were not deployed, and nothing was pushed or published. This user-selected plan supersedes the former Railway target. Hosted acceptance remains required. Start with synthesis disabled: the latest single paid validation did not display a validated model answer.

## Neon

Create a dedicated demo database in a region near Render. Use a direct connection for this small single-instance application, especially for Alembic. Copy the connection string into the backend secret environment, change its driver prefix to `postgresql+psycopg://`, and preserve Neon SSL/channel-binding options. Percent-encode special characters in credentials. Do not put credentials in commands or source files.

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@NEON_HOST/neondb?sslmode=require&channel_binding=require
```

Neon requires no frontend variables. Enable `vector`, or allow migration 0001 to run `CREATE EXTENSION IF NOT EXISTS vector`. With the backend image and secret environment, run `alembic upgrade head`, `alembic current` and `alembic check`. Expected head: `0004`. Do not reset an existing database to deploy.

Startup seeds only an empty library with eight synthetic documents and indexes 18 intents / 234 examples. Existing libraries are preserved. Verify 25 chunks and `vector_dims(embedding)=384` in both vector tables. The legacy chunk column is unbounded `vector`, with dimensions enforced by the embedding adapter; intent examples use `vector(384)`. No schema rewrite is needed. History, feedback and generation counters also persist in PostgreSQL.

The production database was verified from the application image with MindRouter explicitly disabled. Actual results: Neon PostgreSQL 17.11, pgvector 0.8.0, client TLS active, Alembic current/head 0004, eight documents, 25 chunks, 18 intents and 234 semantic examples. All document and intent embeddings are 384-dimensional. Five real FastEmbed retrieval queries returned the expected source in the top three, and the multi-source MFA/remote-work answer mapped both public citations to active PostgreSQL chunks. A second bootstrap added zero documents and zero embeddings, confirming the seeded baseline is idempotent.

Use the retained verifier after migrations and seeding. It is read-only, refuses local database hosts, suppresses MindRouter, and never prints credentials:

```sh
VERIFY_NEON=1 python verify_neon.py
```

For a local application smoke flow, `validate_neon_app.py` checks health, guest authentication, deterministic chat, history, citations and feedback, then removes only the rows it created. The validated SQLAlchemy pool is two persistent connections plus one overflow connection, with pre-ping, a ten-second acquisition/connect timeout and five-minute recycling.

Reference: [Neon pgvector](https://neon.com/docs/extensions/pgvector).

## Render backend

The root `render.yaml` is a readiness template with automatic deploys off. It builds `backend/Dockerfile` with `backend` as context. A Git-linked service requires a separately authorized private repository push; public publication is not needed. A separately authorized private registry image is another option. No remote was created here.

Build: Render builds the Dockerfile; local equivalent is `docker build -t helpdesk-ai-api backend`. Pinned dependencies, model and tokenizer are downloaded at build time. The model cache is baked into the image. Docker excludes `.env` and `.env.*`; never pass keys as build arguments. Leave Docker Command empty to use:

```sh
alembic upgrade head && python -m app.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

Required backend environment:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@NEON_HOST/neondb?sslmode=require&channel_binding=require
JWT_SECRET=REPLACE_WITH_AT_LEAST_32_RANDOM_CHARACTERS
CORS_ORIGINS=["https://YOUR_FRONTEND.vercel.app"]
```

Recommended explicit values (also application defaults):

```dotenv
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONS=384
DATABASE_POOL_SIZE=2
DATABASE_MAX_OVERFLOW=1
MINDROUTER_API_KEY=
MINDROUTER_BASE_URL=https://api.mindrouter.io/v1
MINDROUTER_MODEL=openai/gpt-4.1-nano
MINDROUTER_MAX_OUTPUT_TOKENS=300
GENERATION_USER_DAILY_LIMIT=3
GENERATION_IP_DAILY_LIMIT=8
GENERATION_GLOBAL_DAILY_LIMIT=20
```

Render supplies `PORT`. The image supplies `HF_HUB_OFFLINE=1`, `EMBEDDING_CACHE_DIR=/app/model-cache` and `TIKTOKEN_CACHE_DIR=/app/tokenizer-cache`. No external embedding key is needed. Set the optional MindRouter key only as a backend secret when separately authorized; an empty key preserves deterministic operation.

Optional initial admin: privately set `BOOTSTRAP_ADMIN_EMAIL=admin@example.invalid` and `BOOTSTRAP_ADMIN_PASSWORD=REPLACE_WITH_A_UNIQUE_12_OR_MORE_CHARACTER_PASSWORD`. Verify login, then remove both. Bootstrap does not rotate existing passwords. Never include credentials in portfolio screenshots.

Health route `/health` checks PostgreSQL without loading the model or calling MindRouter. Empty-database bootstrap does embed the seed corpus, so measure startup duration. Runtime uses a lazy singleton model, serialized embedding calls, batches of eight, one worker and a 2+1 DB pool. Do not add workers on 512 MB. PostgreSQL ranks vectors; index maintenance reads IDs rather than every vector.

IP quotas use `request.client.host`. Preserve restrictive Uvicorn proxy defaults until the actual Render forwarding chain is verified. Do not blindly trust X-Forwarded-For or set `FORWARDED_ALLOW_IPS=*`. If only a proxy address is visible, visitors conservatively share the eight-attempt allowance. Verify visitor separation and spoof resistance during hosted acceptance before claiming hosted per-client enforcement. The global cap remains persistent. Ordinary request limits are process-local; use one worker.

Render Free can sleep after 15 idle minutes and take about a minute to wake. Local files are ephemeral; persistent app state lives in Neon. Free usage has limits and is not a production SLA. Check account allowances before creating resources. References: [Free services](https://render.com/docs/free), [Blueprint fields](https://render.com/docs/blueprint-spec). See `resource-final.json` for local measurements, not hosted capacity claims.

## Vercel frontend

Root: `frontend`. Framework: Vite. Install: `npm ci`. Build: `npm run build`. Output: `dist`. The only required frontend environment variable is public:

```dotenv
VITE_API_URL=https://YOUR_BACKEND.onrender.com
```

Use an HTTPS origin without a trailing slash, credentials, path, query or fragment. Production builds reject an absent, non-HTTPS or loopback URL. Never put JWT, database, admin or MindRouter secrets in VITE variables. Set backend CORS to exact frontend origins; authorize individual previews without wildcards. SPA rewrites in `frontend/vercel.json` support refresh/direct routes. Reference: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite).

The local production build uses `https://helpdesk-api.example.invalid` solely to verify compilation and secret exclusion. Rebuild with the actual Render origin before deployment.

## Hosted acceptance before publication

After separate authorization: create Neon; deploy Render with key empty; verify migrations/seed/health; deploy Vercel with actual API origin; set exact CORS. Test anonymous chat, supported topics, unsupported/ambiguous input, pronoun follow-up, history/refresh, citations against current chunks, feedback, library, admin upload/reindex/removal, analytics, direct routes, mobile, API docs, CORS rejection and bundle secrecy. Measure cold starts, memory and proxy identity. Any new paid validation requires a new explicit call allowance.

Capture real hosted screenshots only after these checks. Local images stay labelled local. Re-run tests, migrations and secret scan, then prepare public GitHub only with explicit authorization. No hosted success is claimed.

## Local regression with paid synthesis disabled

```sh
docker compose -f docker-compose.yml -f compose.offline.yml -f compose.feasibility.yml up -d --build
docker compose exec -T api python verify_offline.py
docker compose exec -T api python verify_resources.py
docker compose exec -T api python -m app.evaluate
```

The feasibility overlay applies 512 MB and 0.1 CPU. Run memory-heavy in-process checks sequentially in a fresh key-disabled container, before its web worker has loaded the model. Never run two model processes inside a 512 MB container. Never delete volumes for routine testing.
