# Architecture/refactor audit — checkpoint 6eee220

The baseline is a React/Vite SPA and FastAPI modular monolith, with SQLAlchemy, PostgreSQL 17, pgvector 0.8.6, Alembic 0002, eight synthetic documents and 25 chunks. FastEmbed already provided real local 384-dimensional embeddings.

External dependencies to remove: app/ai.py HTTP generation and embedding clients, provider keys and model configuration, the /chat generation call, provider fixture tests, the generation evaluation runner, and generation-specific documentation. Authentication, source snapshots, document ingestion/reindex/removal, relational history, ownership, feedback, analytics, and the frontend were reusable.

Migration plan: add intent_examples and nullable conversation/message metadata with migration 0003. Keep existing users, documents, vectors and historical messages. Store 180 positive query vectors and 54 negative vectors. Reindex only changed example/model identities. Preserve the original eight Markdown documents under backend/knowledge so a backend-only build can bundle them.

Production flow: normalize → server-side FastEmbed → intent example cosine scores → explicit scope/negative/ambiguity rules → authoritative pgvector evidence lookup → exact approved fact verification → deterministic templates → stored citations/context. No generation client remains.

Anonymous visitors receive isolated temporary bearer sessions automatically; admin authentication remains mandatory for writes. Guest history lasts for the browser session/token lifetime. No public visitor downloads a model or supplies a key.
