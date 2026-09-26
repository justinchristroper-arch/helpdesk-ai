# Verification record

Local checkpoint, 2026-09-27. The repository remains local and the hosted system is not deployed. Results below distinguish retrieval from generated answers.

| Check | Measured result | Scope |
|---|---|---|
| Docker stack | Database and API started, stopped, and restarted with data retained | No volumes deleted |
| PostgreSQL / pgvector | PostgreSQL 17.11, pgvector 0.8.6, Alembic revision 0002 | Real local database |
| Document ingestion | 8 synthetic documents, 25 chunks, 384-dimensional vectors | Admin API to real database |
| Vector storage and search | Fixture round-trip, cosine order, chunk text and metadata checked | backend/verify_storage.py; fixture rows removed |
| Embedding provider | Real local FastEmbed BAAI/bge-small-en-v1.5; finite 384-dimensional vectors | No embedding mock or API key |
| Retrieval evaluation | Hit@5 9/9 supported; after-gate hit 9/9; unsupported gate abstention 3/5 | Real embeddings and pgvector, threshold 0.70; see evaluation-retrieval.json |
| Browser regression | 3 Edge tests passed | Real local auth, document library, analytics, refresh/direct route, mobile; AI-unconfigured safe error |
| Backend tests | 28 passed, 1 opt-in skipped; separate real PostgreSQL test 1 passed | One Starlette/httpx deprecation warning |
| Frontend tests / lint / build | 4 passed / passed / passed | Production bundle built successfully |
| Migration consistency | Alembic current 0002 (head); no new upgrade operations | Existing project database |
| Secret scan | 68 Git-visible files checked; no potential secret patterns found | Local ignored .env and demo credentials excluded |
| API docs / health | /docs 200, /health 200 | ai_configured: false |
| DeepSeek generation | Not run | Key not supplied; API compatibility is documentation-based only |
| Answer support / citation quality | Not measured | Requires real generated answers and review |
| Hosted end-to-end / screenshots | Not run | Vercel, Railway, and hosted database not provisioned |

The 14-question retrieval set contains 9 supported and 5 unsupported questions. Two unsupported questions pass the similarity gate, so the gate alone is insufficient for fallback. The 0.70 threshold was selected using this same small set; these scores do not estimate performance on unseen questions. Citation validity and semantic answer support remain unmeasured.

The original Docker Desktop startup log showed failure removing its dockerInference Unix socket. Docker later created a fresh runtime socket and started; the underlying reason that the old socket could not be removed was not independently established. Separate host-port conflicts on 5432 and 5433 were resolved by configuring this project's database host port as 55432. No other project or Docker volume was changed.

Pending release gates: authenticated DeepSeek request; supported, multi-source, unsupported, and low-relevance RAG answers; citation review; full evaluation; deployment; hosted browser and API regression; hosted screenshots; final checks and secret scan. Do not publish GitHub until those critical checks pass.
