"""Read-only production-database verification with credential-safe output.

Run from ``backend`` only after setting ``VERIFY_NEON=1`` and placing the real
DATABASE_URL in the ignored ``backend/.env``. MindRouter is never used.
"""
import json
import os
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

os.environ["MINDROUTER_API_KEY"] = ""

from app.config import get_settings
from app.db import Session, engine
from app.intents import dataset
from app.models import Chunk, Document, IntentExample
from app.semantic import answer


EXPECTED_TABLES = {
    "alembic_version", "users", "documents", "document_chunks",
    "conversations", "messages", "message_sources", "feedback",
    "intent_examples", "generation_usage",
}
EXPECTED_COLUMNS = {
    "users": {"id", "email", "password_hash", "role", "created_at"},
    "documents": {"id", "title", "filename", "mime_type", "status", "embedding_model",
                  "content_hash", "created_at", "updated_at"},
    "document_chunks": {"id", "document_id", "chunk_index", "page_number", "section",
                        "content", "embedding", "created_at"},
    "intent_examples": {"id", "intent_id", "content", "negative", "embedding_model",
                        "dataset_hash", "embedding"},
    "conversations": {"id", "user_id", "title", "context", "created_at", "updated_at"},
    "messages": {"id", "conversation_id", "role", "content", "outcome", "model",
                 "prompt_version", "intent_id", "diagnostics", "clarification", "created_at"},
    "message_sources": {"id", "message_id", "chunk_id", "document_id", "title", "section",
                        "page_number", "excerpt", "relevance_score", "citation_number"},
    "feedback": {"id", "message_id", "user_id", "rating", "note", "created_at"},
    "generation_usage": {"id", "day", "scope", "identity", "count"},
}
QUESTIONS = [
    ("How do I request VPN access?", "vpn-access-policy.md"),
    ("My MFA is not working.", "mfa-reset-guide.md"),
    ("What should I do if my laptop is damaged?", "laptop-damage-procedure.md"),
    ("How do I request database access?", "database-access-sop.md"),
    ("What is the SLA for a high-priority incident?", "incident-priority-sla.md"),
]


def target_summary():
    url = make_url(get_settings().database_url)
    sslmode = str(url.query.get("sslmode", "")).lower()
    return {
        "host": url.host,
        "database": url.database,
        "driver": url.drivername,
        "ssl_requested": sslmode in {"require", "verify-ca", "verify-full"},
    }


def main():
    if os.getenv("VERIFY_NEON") != "1":
        raise SystemExit("Set VERIFY_NEON=1 to verify the configured production database.")
    target = target_summary()
    if target["host"] in {None, "localhost", "127.0.0.1", "db"}:
        raise SystemExit("Refusing production verification against a local database host.")

    expected_head = ScriptDirectory(str(Path(__file__).parent / "migrations")).get_current_head()
    with Session() as db:
        postgres_version = db.scalar(text("SHOW server_version"))
        pgvector_version = db.scalar(text(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
        server_ssl_view = bool(db.scalar(text(
            "SELECT COALESCE((SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()), false)")))
        ssl_active = bool(db.connection().connection.driver_connection.pgconn.ssl_in_use)
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        inspector = inspect(db.connection())
        tables = set(inspector.get_table_names())
        missing_columns = {
            table: sorted(columns - {column["name"] for column in inspector.get_columns(table)})
            for table, columns in EXPECTED_COLUMNS.items() if table in tables
        }
        missing_columns = {table: columns for table, columns in missing_columns.items() if columns}
        counts = {
            "documents": db.scalar(select(func.count()).select_from(Document)),
            "chunks": db.scalar(select(func.count()).select_from(Chunk)),
            "semantic_examples": db.scalar(select(func.count()).select_from(IntentExample)),
            "intents": db.scalar(select(func.count(func.distinct(IntentExample.intent_id)))),
            "positive_examples": db.scalar(select(func.count()).select_from(IntentExample)
                                            .where(IntentExample.negative.is_(False))),
            "negative_examples": db.scalar(select(func.count()).select_from(IntentExample)
                                            .where(IntentExample.negative.is_(True))),
        }
        chunk_dimensions = [list(row) for row in db.execute(text(
            "SELECT vector_dims(embedding), count(*) FROM document_chunks GROUP BY 1 ORDER BY 1"))]
        intent_dimensions = [list(row) for row in db.execute(text(
            "SELECT vector_dims(embedding), count(*) FROM intent_examples GROUP BY 1 ORDER BY 1"))]

        retrieval = []
        for question, expected_filename in QUESTIONS:
            result = answer(db, question)
            sources = [{
                "document": document.filename,
                "section": chunk.section,
                "score": round(float(score), 6),
            } for chunk, document, score, _ in result.sources[:3]]
            retrieval.append({
                "question": question,
                "outcome": result.outcome,
                "top_document": sources[0]["document"] if sources else None,
                "top_section": sources[0]["section"] if sources else None,
                "top_score": sources[0]["score"] if sources else None,
                "expected_source_in_top_3": any(
                    source["document"] == expected_filename for source in sources),
            })

        citation_result = answer(
            db, "My MFA is broken while I'm working remotely. What should I do?")
        citation_checks = []
        for number, (chunk, document, score, facts) in enumerate(citation_result.sources, 1):
            current_chunk = db.get(Chunk, chunk.id)
            current_document = db.get(Document, document.id)
            citation_checks.append({
                "citation_number": number,
                "document_id_present": bool(document.id),
                "document_title": document.title,
                "chunk_id_present": bool(chunk.id),
                "section": chunk.section,
                "excerpt_present": bool(chunk.content),
                "active_chunk_mapping": bool(
                    current_chunk and current_document and current_document.status == "ready"
                    and current_chunk.document_id == current_document.id
                    and all(fact in current_chunk.content for fact in facts)),
            })

    report = {
        "target": target,
        "connection": "passed",
        "postgresql_version": postgres_version,
        "ssl_active": ssl_active,
        "server_ssl_view": server_ssl_view,
        "pgvector_version": pgvector_version,
        "alembic": {"current": revision, "head": expected_head, "matches": revision == expected_head},
        "schema": {"expected_tables_present": EXPECTED_TABLES <= tables,
                   "missing_tables": sorted(EXPECTED_TABLES - tables),
                   "expected_columns_present": not missing_columns,
                   "missing_columns": missing_columns},
        "counts": counts,
        "vector_dimensions": {"document_chunks": chunk_dimensions,
                              "intent_examples": intent_dimensions},
        "embedding_model": get_settings().embedding_model,
        "external_embedding_api_used": False,
        "retrieval": retrieval,
        "citation_validation": {
            "outcome": citation_result.outcome,
            "answer_contains_public_citations": all(
                f"[{number}]" in citation_result.content
                for number in range(1, len(citation_result.sources) + 1)),
            "sources": citation_checks,
            "all_active_chunk_mappings": bool(citation_checks) and all(
                item["active_chunk_mapping"] for item in citation_checks),
        },
    }

    checks = [
        ssl_active, bool(pgvector_version), revision == expected_head,
        EXPECTED_TABLES <= tables, not missing_columns, counts == {
            "documents": 8, "chunks": 25, "semantic_examples": 234,
            "intents": 18, "positive_examples": 180, "negative_examples": 54,
        },
        chunk_dimensions == [[384, 25]], intent_dimensions == [[384, 234]],
        all(item["expected_source_in_top_3"] for item in retrieval),
        report["citation_validation"]["answer_contains_public_citations"],
        report["citation_validation"]["all_active_chunk_mappings"],
    ]
    report["ready"] = all(checks)
    print(json.dumps(report, indent=2))
    if not report["ready"]:
        raise SystemExit(1)
    engine.dispose()


if __name__ == "__main__":
    main()
