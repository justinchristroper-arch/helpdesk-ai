# Verification record

Local architecture checkpoint, 2026-09-27. Hosted verification is still in progress; GitHub publication is not authorized.

- Real PostgreSQL 17.11 and pgvector 0.8.6; Alembic 0003 at head, no pending model/schema operations.
- Eight preserved synthetic documents and 25 source chunks; server-side FastEmbed creates 384-dimensional vectors.
- Eighteen intents, 180 positive queries and 54 negative examples persist as 234 vectors. Repeated indexing reports zero new embeddings.
- Backend: 51 tests passed with LIVE_SEMANTIC=1 and TEST_DATABASE_URL, including real matching, source-change fallback, vectors, context and multi-source evidence. One Starlette/httpx deprecation warning remains.
- Frontend unit tests: four passed. Lint/build passed. Local Edge browser: four scenarios passed covering immediate anonymous chat, citations, feedback, context, history refresh, unsupported/ambiguous questions, multi-source, public library, mobile, admin upload/reindex/removal and analytics.
- No-API integration: verify_offline.py removes API-key environment variables and blocks non-database socket connections before importing/loading the local model. Supported chat, citations, feedback, history, fallback and follow-up passed with zero external socket attempts. Latest cold complete test flow was 0.688 seconds locally.
- Current 80-case regression: intent Top-1 53/53; Top-3 53/53; supported recall 53/53; returned-evidence Hit@3 53/53; unsupported rejection 21/21; ambiguity 6/6; citation validity 53/53 answered cases; verbatim evidence support 53/53; follow-up 6/6.

All cases and metric definitions are in evaluation-semantic.json. These are inspected synthetic regression cases, not independent estimates of general language accuracy. The initial frozen-rule 16-case validation had two failures (VPN approval duration and a topic-only VPN query); its complete result is preserved in evaluation-initial-validation.json. Both behaviors were corrected. Verbatim support checks quote membership, not independent semantic entailment.

Original Docker startup failed removing a dockerInference socket. The deeper cause was not proven; the engine subsequently recovered. Host-port conflicts were resolved with project port 55432. No database volumes were deleted. Deployment builds use backend-only context to avoid an inaccessible unrelated root test cache on Windows.

Local screenshots are labelled local-semantic-*.png. They are not presented as hosted evidence. Hosted URLs, deployed screenshots, final secret scan and final Git checkpoint will be recorded after the actual deployment and tests.
