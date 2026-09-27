# Deployment runbook

Frontend target: Vercel. The original isolated Railway deployment is blocked by the account's free resource provisioning limit. The user requested evaluation of free alternatives before migration; see [hosting assessment](hosting-options.md). No alternative resources or app deployments have been created. Vercel is linked only. No GitHub push is required. Optional DeepSeek credentials remain backend-only.

## Backend

Build from backend using its Dockerfile/railway.toml. The model and tokenizer download during build; the resulting model cache was approximately 65 MB locally. Runtime uses local files only. Startup applies migrations, seeds bundled demo documents only for a new library, and idempotently indexes intents.

Use PostgreSQL with pgvector, persistent storage, private networking and DATABASE_URL in postgresql+psycopg format. Configure JWT_SECRET and exact CORS_ORIGINS. Set optional DEEPSEEK_API_KEY only in the backend environment; never place it in frontend variables or the image. Use one API worker until ordinary request limits are shared. Verify extension and revision 0004 in the hosted database. PostgreSQL generation counters already work across workers.

Railway could not provision a project, so its hosted pgvector image has not been tested. This is a quota blocker, not a pgvector failure. Neon and Supabase have been evaluated as alternatives; no switch has been made.

## Cost feasibility

Earlier local warm API measurement was approximately 290 MiB RAM, PostgreSQL approximately 35 MiB. The current full in-process offline API test completed in 1.355 seconds with a loaded container; this is not a hosted cold-start SLA. Under a separate 512 MB/0.1 CPU local container limit, the cold flow took 22.794 seconds and peak process RSS was about 338 MiB. Model download is a build-time cost, not a browser action.

Railway account inspection found an active trial with approximately $4.83 credit and 28 days left. Current Railway documentation lists a Free allowance of $1/month and 0.5 GB RAM per service. Continuous operation of API and DB may exceed that credit; no indefinite-free hosting claim is made. Do not upgrade or add a paid plan without approval.

Sources checked: https://docs.railway.com/pricing/plans and https://railway.com/pricing. Actual hosted usage must be measured after deployment.

## Frontend and acceptance

Deploy frontend with VITE_API_URL set to the public HTTPS API origin. Set exact production/preview origins in backend CORS. Test as a fresh anonymous visitor: supported and paraphrased questions, undocumented details, ambiguity, follow-up, multi-source citations, feedback, refresh/history, library, mobile, direct routes, console/API errors and docs. Verify admin controls separately and ensure no secrets in bundles.

Capture actual deployed screenshots only after successful hosted tests. Run final tests/lint/build/migrations/secret scan/Git status. Keep GitHub unpublished until explicitly authorized.
