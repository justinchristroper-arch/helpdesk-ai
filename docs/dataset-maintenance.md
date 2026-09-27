# Maintaining knowledge and intents

The canonical documents are the eight Markdown files in backend/knowledge. Intent records are in backend/data/intents.json; evaluation cases are in backend/data/evaluation.json.

1. Add or update a synthetic document through an administrator or the bundled corpus for a new installation.
2. Add an intent_id, human-readable topic, canonical_question, diverse paraphrases, keywords, and negative_examples. Include symptoms, indirect wording and short queries; avoid copies differing by one token.
3. Set answer_type and evidence entries. Each entry maps the exact stored filename and section and contains reviewed factual sentences copied verbatim from that source. Do not write unsupported facts.
4. Use required_groups for specialized contextual intents, prefer_patterns only for clear scope distinctions, and unsupported_patterns for missing policy facets. These are explainable rules in data, not exact question-to-answer code.
5. Run python -m app.intents against the real database. IDs hash intent, polarity, text and embedding model; unchanged examples reuse vectors. Dataset hashes invalidate stale indexes. Rebuild/restart the API after changing the packaged dataset.
6. Add independent evaluation queries, including nearby negatives and ambiguous forms. Run python -m app.evaluate and review every unexpected answer. Preserve earlier failures and distinguish tuned regression results from fresh validation.
7. Run the backend and browser suites and the no-API verification before deployment.

Document reindex recomputes chunk embeddings locally; it does not automatically approve new answer facts or extract new intents. Removing all documents does not automatically reseed on restart if the intent index already exists. Dataset/corpus changes need review and a deployment; admin uploads alone do not extend the semantic answer scope.

All current data is synthetic. Current coverage: 18 intents, 180 positive examples, 54 negatives, eight documents, 25 source chunks and 80 evaluation cases. The public language scope is English.
