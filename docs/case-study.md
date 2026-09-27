# Portfolio case study — verification in progress

Employees need to find IT procedures and check their authority. A generic cloud chatbot is not necessary for every bounded knowledge task.

HelpDesk AI reuses a real PostgreSQL/pgvector foundation with server-side FastEmbed, curated semantic intent examples, exact source-backed facts and deterministic composition. Optional DeepSeek synthesis selects approved facts for multi-source answers when quota and API balance allow. Users ask natural questions, inspect citations, clarify an ambiguous topic, and continue a lightweight conversation without setting up a model or account.

Engineering decisions include persistent example embeddings, additive migrations, fail-closed verification when approved facts disappear, PostgreSQL-backed generation quotas, backend-controlled citations, isolated anonymous history, admin-only knowledge management, and explicit no-network fallback tests.

The trade-off is narrower flexibility: new documents need reviewed intent/fact mappings, and matching quality depends on coverage. Synthetic benchmark results are reported with definitions and failures, not as general AI accuracy or measured company savings. Optional DeepSeek calls may incur API charges; deterministic answers work without them.

Local behavior is verified. Hosted completion and portfolio screenshot status are recorded in verification.md. Do not describe the project as fully deployed or publish GitHub before hosted acceptance passes.
