# Verification record

Local checks on 2026-09-26. This is not a production completion report.

| Check | Result | Scope |
|---|---|---|
| Backend pytest | 28 passed, 1 skipped | Extraction, chunks, retrieval threshold, citations, provider response validation, auth guards, CORS, limits, relational history/feedback/ownership |
| PostgreSQL/pgvector integration | Not run | Docker Desktop failed startup; TEST_DATABASE_URL unavailable |
| Alembic offline SQL generation | Passed | Immutable initial DDL compiled; not applied to a live database |
| Frontend production build | Passed | TypeScript and Vite |
| Frontend lint | Passed | ESLint |
| Frontend tests | 4 passed | API error/auth handling and guest question/admin-control behavior |
| Dependency audit | 0 vulnerabilities after update | npm audit; time-specific registry result |
| Desktop browser | Passed for guest flow | Page rendered, examples populate input, send opens sign-in, no reported browser errors |
| Mobile browser | Visually checked | 390px viewport screenshot; no horizontal clipping observed |
| Real embeddings / generation | Not run | OpenRouter key not configured |
| Retrieval quality evaluation | Not run | Runner and 12 synthetic cases prepared; no invented metrics |
| Public end-to-end | Not run | No deployment yet |

Relational persistence tests use SQLite and do not establish pgvector correctness. Provider fixture tests check application behavior, not the live provider. Citation validation checks identifiers and quote membership; semantic correctness still needs human evaluation.

Pytest emits a Starlette/httpx deprecation warning. It does not affect the passing tests, but the test client dependency should be revisited before upgrading further.

Screenshots: `screenshots/desktop.png` and `screenshots/mobile.png`.

## Remaining release work

1. Restore a working Docker Linux engine or provide a reachable PostgreSQL 17 + pgvector database.
2. Run Alembic against it; verify schema, extension, vector round-trip, source retention, and real retrieval.
3. Configure OpenRouter, create accounts, ingest all eight documents, and evaluate the 12-case set.
4. Review semantic answer support and tune the provisional threshold.
5. Configure Railway and Vercel; deploy and run the public acceptance checklist.
6. Record real URLs, GitHub repository, deployed commit, and final results.
