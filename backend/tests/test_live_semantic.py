"""Opt-in real cached FastEmbed + seeded PostgreSQL checks; no provider mocks."""
import os
import pytest
from sqlalchemy import select, func
from app.db import Session
from app.intents import index_intents
from app.models import Chunk, Document, IntentExample
from app.semantic import answer

pytestmark = pytest.mark.skipif(os.getenv("LIVE_SEMANTIC") != "1", reason="Requires real seeded pgvector and cached FastEmbed")


@pytest.mark.parametrize("query,intent,outcome", [
    ("How do I request VPN access?", "vpn_request", "answered"),
    ("I need internal systems from outside the office", "vpn_request", "answered"),
    ("vpm conection error", "vpn_connection", "answered"),
    ("My authenticator stopped working", "mfa_reset", "answered"),
    ("My work account is locked", "account_unlock", "answered"),
    ("What is the laptop reimbursement limit?", None, "fallback"),
    ("What is my manager's email address for VPN approval?", None, "fallback"),
    ("I need access", None, "clarification"),
    ("VPN help", None, "clarification"),
    ("vpn", None, "clarification"),
    ("How many hours does VPN approval take?", None, "fallback"),
])
def test_real_matching(query, intent, outcome):
    with Session() as db:
        result = answer(db, query)
        assert (result.intent_id, result.outcome) == (intent, outcome)
        assert all(all(fact in c.content for fact in facts) for c,d,s,facts in result.sources)


def test_static_index_reuses_vectors():
    with Session() as db:
        assert index_intents(db)["new_embeddings"] == 0
        assert db.scalar(select(func.count()).select_from(IntentExample)) == 234


def test_multi_source_and_context():
    with Session() as db:
        result = answer(db, "My MFA is broken while I'm working remotely. What should I do?")
        assert len(result.sources) == 2
        assert {d.filename for c,d,s,f in result.sources} == {"mfa-reset-guide.md", "remote-work-checklist.md"}
        vpn = answer(db, "How do I request VPN access?")
        follow = answer(db, "What are the requirements?", vpn.context)
        assert follow.intent_id == "vpn_request" and follow.diagnostics["used_context"]
        denied = answer(db, "What if my manager rejects it?", vpn.context)
        assert denied.outcome == "fallback"


@pytest.mark.parametrize("change", ["remove", "rewrite"])
def test_missing_or_changed_source_cannot_answer(change):
    with Session() as db:
        try:
            doc = db.scalar(select(Document).where(Document.filename == "vpn-access-policy.md"))
            if change == "remove":
                doc.status = "removed"
            else:
                chunk = db.scalar(select(Chunk).where(Chunk.document_id == doc.id, Chunk.section == "Request VPN access"))
                chunk.content = "A changed document without the approved facts."
            db.flush()
            assert answer(db, "How do I request VPN access?").outcome == "fallback"
        finally:
            db.rollback()
