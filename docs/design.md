# Architecture

React/TypeScript/Vite → FastAPI → PostgreSQL 17 + pgvector. FastEmbed runs in the API process using a cached ONNX model. Optional MindRouter synthesis runs only after retrieval and fact validation for multi-source answers or supported long questions with at least two facts.

## Matching and evidence

The JSON dataset contains 18 intent records with canonical questions, diverse paraphrases, keywords, negative examples, answer types, source sections and exact reviewed facts. Source files live in backend/knowledge. IntentExample stores positive and negative vectors, model identity and dataset hash. Only current-hash examples participate; unchanged examples reuse embeddings.

Each request embeds one normalized query. Limited follow-ups add the active topic (or canonical question for generic continuations). Explicit topic changes do not inherit context. A fallback clears topic context. No complex coreference model is used.

The matcher takes maximum cosine similarity per intent and polarity. Required scope groups remove inapplicable specialized intents (e.g. remote MFA requires both topics). Clear lexical specificity may choose a candidate within 0.08 of the best score. Negative examples within 0.025 of the chosen positive score reject it. Unsupported facet patterns reject details absent from the policy, such as VPN approval duration.

Central settings: minimum intent score 0.72; without keyword support 0.81; ambiguity margin 0.025 (0.06 for short queries); FAQ score 0.94; source cosine floor 0.50; top-k 3. These are tuned demo gates, not calibrated confidence. Underspecified access and topic-only queries clarify using actual matching intents.

Evidence lookup uses the already indexed canonical-question vector and exact mapped filename/section, filtering ready documents and embedding model. This avoids discarding valid symptom queries solely because source wording differs. The semantic path also records broad top-k document candidates; the FAQ path omits that extra query. Identical normalized chunks are deduplicated. Every fact must be an exact substring of the selected chunk, or the complete answer falls back.

Templates change presentation only, selected by a deterministic query hash. The factual sentences come from reviewed knowledge records and current source text. Multi-source answers require every mapped source. Document deletion or changed facts invalidate future answers; prior message snapshots remain.

When synthesis is eligible and MINDROUTER_API_KEY is configured, the backend atomically reserves daily global, user and IP usage in PostgreSQL before one MindRouter request. The request contains only the configured model, a concise question-and-approved-facts message, and the 300-token output limit. It omits sampling controls, structured output, reasoning parameters, tools and provider extensions. Each approved fact receives an internal `F#` ID tied to its retrieved chunk and public citation number. The model may paraphrase, but every output line must end with known supporting IDs. Deterministic validation rejects missing or malformed IDs, incomplete source coverage, unsupported numbers/contact data/policy terms, weak lexical evidence overlap, excessive output and evidence that is no longer active in PostgreSQL. Accepted internal markers are replaced with backend-owned public citation numbers. Missing key, exhausted quota, provider error, invalid response or missing evidence uses deterministic composition. Reservations count attempted calls, including failures.

## Persistence and access

Migration 0003 adds intent_examples, conversation context, detected intent, diagnostics, and clarification choices. Migration 0004 adds shared daily generation counters without rewriting the earlier corpus. Context records active intent/topic, recent documents, and recent query. MessageSource preserves actual title, page, section, chunk ID, excerpt and score.

Anonymous visitors create a guest bearer session without registration; ownership checks isolate history/feedback. Tokens expire after eight hours and sessionStorage is scoped to the browser tab/session. Administrator credentials are separate; anonymous uploads are prohibited. The demo has process-local rate limits and should use one worker until distributed limits exist.

## Limits

Narrow English synthetic corpus, curated source mappings, no arbitrary long-form generation, no guarantee of semantic correctness on unseen queries. Quote validity is measurable but is not independent entailment assessment. Hosting, database retention and operational costs still apply.
