# Deployment runbook

Frontend target: Vercel. Backend/database target: isolated Railway project using PostgreSQL with pgvector. No GitHub push is required: deploy local source with the CLIs. No AI provider secrets are used.

## Backend

Build from backend using its Dockerfile/railway.toml. The model and tokenizer download during build; the resulting model cache was approximately 65 MB locally. Runtime uses local files only. Startup applies migrations, seeds bundled demo documents only for a new library, and idempotently indexes intents.

Use a pgvector/pgvector:pg17 database service with a persistent /var/lib/postgresql/data volume, private networking, strong POSTGRES_PASSWORD, and DATABASE_URL in postgresql+psycopg format. Configure JWT_SECRET and exact CORS_ORIGINS. Never put these in frontend variables. Use one API worker. Verify extension and revision 0003 in the hosted database.

Before introducing a different database provider, verify whether the Railway pgvector image works. Supabase is only a fallback if this setup is impractical; no switch has been made.

## Cost feasibility

Local warm API measured approximately 290 MiB RAM, PostgreSQL approximately 35 MiB. The complete cold in-process offline API verification took about 1.05 seconds locally; this is not a hosted cold-start SLA. Model download is a build-time cost, not a browser action.

Railway account inspection found an active trial with approximately $4.83 credit and 28 days left. Current Railway documentation lists a Free allowance of $1/month and 0.5 GB RAM per service. Continuous operation of API and DB may exceed that credit; no indefinite-free hosting claim is made. Do not upgrade or add a paid plan without approval.

Sources checked: https://docs.railway.com/pricing/plans and https://railway.com/pricing. Actual hosted usage must be measured after deployment.

## Frontend and acceptance

Deploy frontend with VITE_API_URL set to the public HTTPS API origin. Set exact production/preview origins in backend CORS. Test as a fresh anonymous visitor: supported and paraphrased questions, undocumented details, ambiguity, follow-up, multi-source citations, feedback, refresh/history, library, mobile, direct routes, console/API errors and docs. Verify admin controls separately and ensure no secrets in bundles.

Capture actual deployed screenshots only after successful hosted tests. Run final tests/lint/build/migrations/secret scan/Git status. Keep GitHub unpublished until explicitly authorized.
