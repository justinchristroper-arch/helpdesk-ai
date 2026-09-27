# Free hosting assessment — 2026-09-27

Status: assessment only. The user requested a report before migration. No Render, Neon, Supabase or registry resource has been created. GitHub remains unpublished.

## Current blocker

Railway rejected creation of the isolated HelpDesk-AI project: `Free plan resource provision limit exceeded. Please upgrade to provision more resources!` A subsequent project listing showed no HelpDesk-AI project. Existing projects were left untouched. This is an account provisioning limit, not a demonstrated pgvector incompatibility.

Vercel project `justin-c/helpdesk-ai` is linked locally, but has no deployment from this work. There is no hosted application URL or hosted end-to-end result yet.

## Recommendation and alternatives

| Component | Proposed free option | Limits and implications |
| --- | --- | --- |
| Frontend | Vercel Hobby | Suitable for this personal, noncommercial portfolio; account quotas still apply. |
| API | Render Free web service | 512 MB RAM, 0.1 CPU, 750 instance hours per workspace/month shared with other free services. Sleeps after 15 minutes idle; waking can take about a minute. Ephemeral disk requires the model to be baked into the image. |
| Database | Neon Free PostgreSQL + pgvector | 0.5 GB per project, 100 CU-hours/month/project and 5 GB public egress/month/project. Compute suspends after five idle minutes and resumes on demand. Storage and usage quotas still require monitoring. |
| Database alternative | Supabase Free PostgreSQL + pgvector | 500 MB database, two active free projects, 5 GB egress. Low-activity projects can pause after seven days, which is less convenient for an intermittently visited portfolio. |

Recommend Vercel + Render + Neon for an initial free demo, subject to actual account availability and hosted verification. This retains the current PostgreSQL/pgvector architecture and local FastEmbed inference. It does not promise instant responses after inactivity or production availability.

Render Free PostgreSQL is unsuitable for this persistent demo because it expires after 30 days. Current Hugging Face documentation requires a paid account tier to create new Docker/Gradio compute Spaces; its documented outbound port restrictions also complicate direct PostgreSQL connections. Neither is recommended here.

No paid subscription, payment-method addition or automatic paid upgrade is proposed. Render documentation says overages can be billed when a payment method exists; without one, service can instead be suspended. Existing account billing settings and shared quotas must be checked before provisioning.

## Measured local feasibility

The existing Docker stack was restored without deleting volumes. Real storage verification passed with pgvector 0.8.6 and migration 0003, including cosine search and metadata checks.

Using `compose.feasibility.yml`, a temporary API container was limited to 512 MB and 0.1 CPU. The cold local no-API verification passed guest creation, grounded answer, citations, feedback, history, fallback and follow-up. It recorded zero non-database socket connection attempts and no API-key environment variables. Total test-flow time: **22.794 seconds**. Peak process RSS: **346072 KiB (about 338 MiB)**.

This is one sequential local test, not a hosted benchmark, per-question latency measurement, total container memory measurement, or concurrency guarantee. Render scheduling, service wake-up, external database latency and memory headroom remain unverified. The model is loaded on the server; visitors do not download it.

## Migration steps after the user reviews this report

1. Check free account quotas and billing settings. Confirm private image registry availability; do not publish repository or image publicly.
2. Provision Neon Free, enable pgvector, run migration 0004, and validate real vectors, retrieval and generation counters.
3. Deploy the backend to Render using a private prebuilt image with its model cache. Render supports private registries; Docker Personal includes one private repository, subject to account availability. Store database credentials, JWT secret and optional DeepSeek key only in server configuration. DeepSeek API balance is currently insufficient (HTTP 402); deterministic retrieval remains available.
4. Deploy frontend to Vercel with the real API URL and exact CORS origins.
5. Measure hosted cold/warm response behavior, memory, startup reliability and modest concurrent traffic. Run the complete hosted regression, scan bundles for secrets, and capture real deployed screenshots.

If the free API cannot run reliably, report that result before choosing a different service or any paid plan. Hosted verification and project completion remain pending.

## Official references checked

- [Vercel Hobby](https://vercel.com/docs/plans/hobby)
- [Render compute plans](https://render.com/docs/compute-plans), [free services](https://render.com/docs/free), [billing FAQ](https://render.com/docs/faq), [private image deployment](https://render.com/docs/deploying-an-image)
- [Neon pricing](https://neon.com/pricing), [plans](https://neon.com/docs/introduction/plans), [pgvector](https://neon.com/docs/extensions/pgvector), [scale to zero](https://neon.com/docs/introduction/scale-to-zero)
- [Supabase pricing](https://supabase.com/pricing), [free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview)
- [Docker pricing FAQ](https://www.docker.com/pricing/faq/)
