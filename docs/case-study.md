# HelpDesk AI — portfolio case study (implementation draft)

## Problem and approach

Internal IT knowledge is useful only when employees can find the correct procedure and verify its authority. This project models a company with synthetic policies for VPN, MFA, damaged laptops, software, database access, incidents, locked accounts, and remote work.

The solution uses retrieval-augmented generation to narrow answers to approved source text. It exposes sources instead of asking users to trust fluent text. When retrieval or citation validation fails, it returns an explicit no-answer response.

## Engineering decisions

- A modular monolith keeps ingestion, retrieval, chat, and authorization in one service without distributed infrastructure.
- PostgreSQL holds relational records and vectors, reducing operational overhead for a small portfolio corpus.
- Exact cosine search is appropriate for the initial corpus; an approximate index should follow measured scale needs.
- Page/section-aware chunks preserve source locations. A 700-token window with 100-token overlap is configurable and must be evaluated rather than assumed optimal.
- Model-generated source identifiers are checked server-side. Exact supporting quotes must appear in the retrieved source. This is a useful safeguard, not proof of semantic correctness.
- Historical citations contain evidence snapshots so document removal does not erase the basis of an earlier answer.

## Results and remaining evidence

Local FastEmbed, PostgreSQL/pgvector ingestion and search, and browser flows have been verified. The small synthetic retrieval set measured Hit@5 of 9/9 supported cases and retrieval-gate abstention of 3/5 unsupported cases. Generated-answer quality, deployment, and hosted end-to-end results are pending. No ROI or production-readiness claim is made.

## Portfolio-ready description

HelpDesk AI is an internal IT knowledge assistant built with React, FastAPI, and PostgreSQL/pgvector. It implements document ingestion, vector retrieval, context-grounded generation, inspectable citations, and explicit fallback behavior using a synthetic policy library. The project emphasizes source traceability, practical access controls, and transparent evaluation.

## CV bullets (use after describing the current verification status)

- Implemented a RAG knowledge assistant using React, FastAPI, PostgreSQL/pgvector, and local FastEmbed, with document ingestion and a DeepSeek generation adapter awaiting live validation.
- Designed citation validation, retrieval audit records, and low-evidence fallbacks to make AI responses inspectable.
- Modeled IT knowledge workflows and added administrator document management, conversation history, feedback, and usage analytics.

Do not add “deployed,” quality metrics, or business impact until supported by recorded results.

## Interview talking points

1. Why RAG instead of a generic chatbot? Policy answers need current, inspectable evidence and a clear abstention path.
2. Why pgvector? The corpus is small and relational metadata, conversations, and vectors benefit from one transactional database.
3. What does the retrieval score mean? Cosine similarity ranks embedding proximity; it is not calibrated confidence.
4. Can citations prevent hallucination? They verify source identity and quote membership, but cannot establish entailment by themselves.
5. What changes at scale? Background ingestion, shared rate limits, approximate indexes, observability, versioned document approval, and independent semantic evaluation.
6. What remains before production? Strong identity, session controls, retention policies, cost controls, security testing, backups, and operational ownership.
