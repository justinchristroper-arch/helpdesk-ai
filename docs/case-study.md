# HelpDesk AI — Evidence-First IT Knowledge Assistant

## Project description

Built an evidence-first IT knowledge assistant using FastEmbed, PostgreSQL/pgvector, semantic intent matching, deterministic grounding, backend-controlled citations, and optional cost-bounded GPT-4.1 Nano synthesis through MindRouter. This is a synthetic portfolio demonstration, not a company deployment. The optional real synthesis path remains unverified; deterministic functionality is independently tested.

## Business problem / AS-IS / TO-BE

AS-IS scenario: employees search separate IT documents, rephrase questions for colleagues, and must locate the actual source before acting. This is a proposed problem statement, not a measured employer study.

TO-BE demonstration: ask a natural-language IT question, receive reviewed source-backed steps or a clarification, inspect the cited excerpt, and give feedback. If evidence is missing, the assistant says so. No productivity improvement or ROI has been measured.

## Technical and architecture summary

React/Vite → FastAPI → server-side FastEmbed (384 dimensions) → PostgreSQL cosine similarity over positive/negative intent examples and mapped chunks → evidence gate → deterministic composer → optional single-call MindRouter paraphrase → validated backend citations.

History, feedback, excerpts, vectors, request limits and daily reservations persist in PostgreSQL. Administrators manage documents; public guests have isolated bearer sessions. The deployment target is one Vercel Services project (Vite at `/`, FastAPI at `/api`) plus Neon. Hosted acceptance is pending; see [the current runbook](vercel-deployment.md).

## Engineering decisions and cost controls

- Local embeddings avoid external embedding charges and work with runtime inference networking blocked.
- Reviewed intent/fact mappings favor inspectability over open-domain flexibility; uploads do not automatically become answer policy.
- A supported answer remains available without a key. Unsupported questions do not invoke generation.
- Atomic PostgreSQL quotas count attempts, including failures: 3/user, 8/IP, 20/global per UTC day; output is capped at 300 tokens. No retries, agents, rerankers or second-pass calls.
- Fact-ID grammar is normalized and checked; public citations come from database metadata. Lexical grounding is conservative and heuristic, not semantic proof.
- Each warm function instance reuses a lazy singleton model with serialized inference. Assets are prepared at build time. Vercel uses NullPool to avoid retaining idle connections per instance; local Docker keeps its 2+1 pool.

## Limitations

English-focused synthetic corpus; 18 curated intents; no OCR, enterprise SSO or retention automation. Paraphrase checks can reject valid answers and cannot guarantee every conceivable unsupported claim is caught. The final paid call returned HTTP 200 but failed sentence formatting. That shape was corrected offline with no paid retry; real synthesis remains unverified. Serverless cold starts and free-tier usage limits remain constraints. Regression scores are not general language accuracy or a production SLA.

## CV bullets

- Built a source-backed IT assistant with React, FastAPI, local FastEmbed embeddings and PostgreSQL/pgvector across 18 reviewed intents and eight synthetic policy documents.
- Implemented evidence gates, citation-to-chunk validation, isolated history, feedback and admin knowledge management, with real database and browser regression coverage.
- Added optional MindRouter synthesis with atomic daily quotas, a 300-token cap and deterministic fallback; documented the live-validation boundary without overstating success.

## Interview talking points

- Why combine semantic matching with reviewed facts instead of generating company policy?
- How does the app remain useful when a paid provider is missing, unavailable or out of quota?
- How do advisory transaction locks prevent concurrent reservations exceeding daily caps?
- Why separate real chunk membership, inspected regression performance and semantic correctness?
- What did real tests show? Transport success is not application success; one-call budgets matter.
- What is needed for enterprise use? Identity, retention, threat assessment, observability, distributed limits and independent evaluation.
- Why is hosted acceptance separate? TLS, CORS, proxy identity, cold starts, memory, actual URLs and deployed screenshots still need measurement.
