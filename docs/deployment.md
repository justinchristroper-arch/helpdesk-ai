# Deployment runbook

Status: not deployed. Keep the repository local until real generation and the complete hosted system pass verification.

## Database and API on Railway

1. Check the current Railway plan, image support, persistent volume, and RAM allowance. FastEmbed caches its model inside the API image; measure API memory before selecting a service size. Do not assume a no-cost deployment. If a pgvector-enabled Railway PostgreSQL image/volume is impractical, evaluate Supabase PostgreSQL with pgvector before changing the architecture.
2. Provision PostgreSQL 17 with a pgvector-enabled image and persistent volume. Confirm CREATE EXTENSION IF NOT EXISTS vector, extension version, and a 384-dimensional vector round-trip before migration. Do not use destructive volume commands.
3. Deploy the API from backend using its Dockerfile. Set private DATABASE_URL with postgresql+psycopg://, JWT_SECRET, DEEPSEEK_API_KEY, AI_PROVIDER=deepseek, and an exact JSON array in CORS_ORIGINS. Keep all keys server-side. API startup applies Alembic migrations; inspect logs and check /health and /docs.
4. Use one worker while rate limiting is process-local. Configure DeepSeek account spending limits. Create demo users privately and ingest only the eight synthetic documents. Verify chunks, model identity, and source views in the hosted database.

## Frontend on Vercel

1. After local DeepSeek E2E succeeds, import the repository with root frontend, build command npm run build, and output dist. Set VITE_API_URL to the Railway HTTPS API origin. Never put provider keys in VITE_ variables.
2. Deploy a preview and add its exact origin to API CORS. Verify direct routes and refresh. Promote only after the full hosted acceptance tests pass.

## Hosted acceptance

- Real employee chat: supported, multi-source, unsupported, and low-relevance questions; inspect answer grounding and citation mapping.
- History survives refresh and is isolated by account; feedback persists; admin analytics reflect events.
- Document library and source excerpts work; admin upload/reindex/removal works with synthetic content.
- Mobile layout and navigation work; direct routes refresh; CORS permits only configured origins; /docs loads.
- No provider key appears in frontend bundles, logs, screenshots, or Git. Capture real screenshots from the deployed application only after these checks.
- Run backend/frontend tests, browser regression, lint, build, migration check, secret scan, and Git status. Record exact results and hosted URLs in verification.md.

DeepSeek credentials have not yet been supplied, and neither hosting service is provisioned. No hosted behavior or portfolio screenshot is claimed.
