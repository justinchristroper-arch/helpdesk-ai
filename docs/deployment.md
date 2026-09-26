# Deployment runbook

Status: not deployed. Do not publish the UI as a working AI demo before validating the API, database, and provider.

## Railway database and API

1. Create a PostgreSQL 17 service using a pgvector-enabled image (`pgvector/pgvector:pg17`) and a persistent volume mounted at `/var/lib/postgresql/data`. Configure a strong password and private network access. Confirm image suitability and Railway resource costs in the account before provisioning.
2. Verify `CREATE EXTENSION IF NOT EXISTS vector` and `SELECT extversion FROM pg_extension WHERE extname='vector'`. If extension installation fails, fix the image before proceeding.
3. Create an API service from this repository with root directory `backend`. It uses `Dockerfile` and `railway.toml` in that directory.
4. Set `DATABASE_URL` using the private hostname and `postgresql+psycopg://` scheme; configure `JWT_SECRET`, `OPENROUTER_API_KEY`, `EMBEDDING_MODEL`, `LLM_MODEL`, and `CORS_ORIGINS` as a JSON array containing the exact frontend origin. Do not expose these through Vite variables.
5. Use one replica/worker for the current in-memory rate limiter. Apply provider spending limits. Docker startup runs migrations before serving traffic. Review the migration logs and `/health`; an HTTP 200 alone does not prove working AI.
6. Create admin and employee users with the management command from a Railway shell. Set demo employee credentials intentionally; do not publish administrator credentials.
7. Seed the eight synthetic Markdown documents using the admin interface or local `seed.py` with `API_URL` pointing to Railway. Validate every upload and its source view.

## Vercel frontend

1. Import the Git repository. Set root directory to `frontend`, build command `npm run build`, and output directory `dist`.
2. Set `VITE_API_URL` to the public HTTPS Railway API origin before building.
3. Deploy a preview. Add its exact origin to the API CORS list if testing there. Do not use wildcard CORS to support arbitrary previews.
4. Run the public flow below. Only after it passes, deploy/promote production and update CORS to the intended production origin.

## Public acceptance checklist

- Health confirms storage connectivity; API docs at `/docs` load.
- An employee can sign in, ask a VPN question, receive a supported answer, and open genuine source evidence.
- A question about parental leave returns fallback; P1 guaranteed-resolution trap does not invent an SLA.
- Refresh restores history. Another account cannot read it by changing IDs.
- Feedback persists and analytics update from actual events.
- Admin can ingest PDF/TXT/Markdown, reject invalid/empty files, reindex, and remove a source.
- Removed sources disappear from future retrieval while earlier citations retain snapshots.
- Unauthorized users receive 401; employees receive 403 for admin operations.
- Unapproved origins receive no CORS permission; frontend bundles contain no provider key.
- Mobile navigation and source inspection work; no unhandled console errors.
- Evaluate the 12-case set using actual embeddings and generation, record results, and review support manually.
- Record deployed commit, URLs, test evidence, remaining limitations, and secret-free Git status.

## Current environment blockers

Docker Desktop startup on the development machine fails inside its Inference Manager socket initialization. No database volumes were removed or reset. A working Docker engine or reachable PostgreSQL+pgvector database is required.

An OpenRouter key and authorized Railway/Vercel project configuration have not yet been supplied in the project environment. Do not paste secrets into chat; configure them locally or in the providers' secret settings.
