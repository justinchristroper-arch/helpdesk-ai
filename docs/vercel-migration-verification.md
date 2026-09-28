# Vercel migration verification — 2026-09-28

The implementation targets one Vercel Services project and the existing Neon database. This records local checks only until a hosted result is explicitly added.

- Full Linux backend suite against local pgvector: **176 passed**, none skipped. Includes concurrent shared request limits (3 accepted, 7 rejected), real semantic matching, persisted generation caps, vector storage, source changes and follow-ups.
- Frontend: **6 passed**, lint passed, production build passed. Output: JS 285.77 kB (90.03 kB gzip), CSS 15.46 kB.
- Real Neon: migration current/head **0005**, Alembic check clean, PostgreSQL 17.11, pgvector 0.8.0, client TLS active. Existing 8 documents, 25 chunks, 18 intents and 234 examples preserved, all 384-dimensional.
- Five Neon retrieval questions returned the expected source; two MFA/remote-work citations mapped to active PostgreSQL chunks. Guest chat, two persisted history messages and feedback passed; temporary application rows were cleaned precisely.
- Packaged pinned FastEmbed assets: **68,860,289 bytes** including tokenizer. Query inference passed in Linux with networking disabled, a read-only filesystem and writable `/tmp` only. Model instance was reused. Local cold embedding 1.447 s, warm embedding 0.009 s, process peak RSS 335,076 KiB. These are local measurements, not Vercel latency/memory claims.
- Initial non-root model check failed because downloaded files were owner-only. Build now normalizes asset read permissions; the full suite passed after correction.
- Warning: upstream Starlette TestClient/httpx deprecation; no application failure. Read-only ONNX telemetry emitted an informational persistence warning and used an in-memory identifier; embedding succeeded.
- Production application API target is `/api`. The bundled React Router library contains two `http://localhost` constants used as URL parsing bases, not outgoing API endpoints. No application localhost backend target is present.
- Paid generation calls during migration: **0**. MindRouter remains disabled and hosted synthesis unverified.

Still required: actual Vercel build/package evidence, deployed API acceptance, clean public-browser E2E, mobile, cold start and final secret/privacy checks. The project is not yet verified for public repository publication or a live portfolio claim.
