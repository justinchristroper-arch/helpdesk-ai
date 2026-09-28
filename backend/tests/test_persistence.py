"""Relational API tests use SQLite; vector retrieval is tested separately on Postgres."""
import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import current_user
from app.db import get_db
from app.main import app
from app.models import Base, Conversation, Feedback, Message, User


@pytest.fixture
def persisted():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id="u1", email="one@example.test", password_hash="unused", role="employee")
        other = User(id="u2", email="two@example.test", password_hash="unused", role="employee")
        db.add_all([user, other])
        db.flush()
        db.add(Conversation(id="c1", user_id=user.id, title="VPN request"))
        db.flush()
        db.add(Message(id="m1", conversation_id="c1", role="assistant", content="Please ask IT.", outcome="fallback"))
        db.commit()
        def dependency():
            yield db
        app.dependency_overrides[get_db] = dependency
        app.dependency_overrides[current_user] = lambda: user
        try:
            yield TestClient(app), db, other
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def test_conversation_history_persists(persisted):
    client, db, _ = persisted
    db.expire_all()
    assert client.get("/conversations").json()[0]["title"] == "VPN request"
    assert client.get("/conversations/c1").json()[0]["content"] == "Please ask IT."


def test_feedback_updates_without_duplicates(persisted):
    client, db, _ = persisted
    assert client.put("/messages/m1/feedback", json={"rating": 1}).status_code == 200
    assert client.put("/messages/m1/feedback", json={"rating": -1, "note": "Needs better evidence"}).status_code == 200
    records = list(db.scalars(select(Feedback)))
    assert len(records) == 1
    assert records[0].rating == -1


def test_other_user_cannot_read_or_rate_conversation(persisted):
    client, _, other = persisted
    app.dependency_overrides[current_user] = lambda: other
    assert client.get("/conversations/c1").status_code == 404
    assert client.put("/messages/m1/feedback", json={"rating": 1}).status_code == 404
    assert client.get("/conversations").json() == []


def test_analytics_counts_and_safe_generation_status(persisted):
    client, db, _ = persisted
    user = db.get(User, "u1")
    user.role = "admin"
    for ident, outcome, state in [("direct", "answered", "quota_or_storage"),
                                   ("synth", "answered", "used"),
                                   ("clarify", "clarification", None)]:
        db.add(Message(id=ident, conversation_id="c1", role="assistant", content="Synthetic test.",
                       outcome=outcome, diagnostics={"generation": {"state": state, "private": "internal-only"}}))
    db.commit()
    client.put("/messages/m1/feedback", json={"rating": 1})
    stats = client.get("/analytics").json()
    assert (stats["total_questions"], stats["answered"], stats["deterministic_answers"],
            stats["synthesized_answers"], stats["fallbacks"], stats["clarifications"]) == (4, 2, 1, 1, 1, 1)
    assert stats["feedback_count"] == 1 and stats["positive_feedback_percent"] == 100
    messages = client.get("/conversations/c1").json()
    assert next(m for m in messages if m["id"] == "direct")["synthesis_status"] == "limited"
    assert "internal-only" not in str(messages)
