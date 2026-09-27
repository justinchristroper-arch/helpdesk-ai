# Portfolio case study — verification in progress

Employees need to find IT procedures and check their authority. A generic cloud chatbot is not necessary for every bounded knowledge task.

HelpDesk AI reuses a real PostgreSQL/pgvector foundation and replaces external generation with server-side FastEmbed, curated semantic intent examples, exact source-backed facts and deterministic composition. Users ask natural questions, inspect citations, clarify an ambiguous topic, and continue a lightweight conversation without setting up a model or account.

Engineering decisions include persistent example embeddings, additive migrations, fail-closed verification when approved facts disappear, isolated anonymous history, admin-only knowledge management, and explicit no-network inference tests.

The trade-off is narrower flexibility: new documents need reviewed intent/fact mappings, and matching quality depends on coverage. Synthetic benchmark results are reported with definitions and failures, not as general AI accuracy or measured company savings. Zero external AI API cost does not imply zero infrastructure cost.

Local behavior is verified. Hosted completion and portfolio screenshot status are recorded in verification.md. Do not describe the project as fully deployed or publish GitHub before hosted acceptance passes.
