"""Real PostgreSQL shared quota reservations; no external provider request."""
import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app import generation
from app.config import Settings
from app.db import Session
from app.models import GenerationUsage

pytestmark = pytest.mark.skipif(os.getenv("LIVE_SEMANTIC") != "1", reason="Requires migrated PostgreSQL")


def test_persisted_user_and_ip_daily_limits(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: Settings(
        _env_file=None, jwt_secret="test-secret-with-at-least-32-characters",
        generation_user_daily_limit=1, generation_ip_daily_limit=1,
        generation_global_daily_limit=10000))
    user, other, ip = str(uuid4()), str(uuid4()), str(uuid4())
    day = datetime.now(timezone.utc).date()
    try:
        assert generation.reserve(user, ip)
        assert not generation.reserve(user, ip)
        assert not generation.reserve(other, ip)
        with Session() as db:
            rows = list(db.scalars(select(GenerationUsage).where(
                GenerationUsage.day == day, GenerationUsage.scope == "user", GenerationUsage.identity == user)))
            assert len(rows) == 1 and rows[0].count == 1
    finally:
        import hashlib
        with Session.begin() as db:
            db.execute(delete(GenerationUsage).where(GenerationUsage.day == day,
                GenerationUsage.scope == "user", GenerationUsage.identity.in_([user, other])))
            db.execute(delete(GenerationUsage).where(GenerationUsage.day == day,
                GenerationUsage.scope == "ip", GenerationUsage.identity == hashlib.sha256(ip.encode()).hexdigest()))
            global_row = db.scalar(select(GenerationUsage).where(GenerationUsage.day == day,
                GenerationUsage.scope == "global", GenerationUsage.identity == "all"))
            if global_row:
                global_row.count -= 1


def test_global_daily_limit_blocks_all_users(monkeypatch):
    day = datetime.now(timezone.utc).date()
    limit = 1
    with Session.begin() as db:
        row = db.scalar(select(GenerationUsage).where(GenerationUsage.day == day,
            GenerationUsage.scope == "global", GenerationUsage.identity == "all"))
        original = row.count if row else None
        if row is None:
            db.add(GenerationUsage(day=day, scope="global", identity="all", count=limit))
        else:
            limit = max(row.count, 1)
            row.count = limit
    try:
        monkeypatch.setattr(generation, "get_settings", lambda: Settings(
            _env_file=None, jwt_secret="test-secret-with-at-least-32-characters",
            generation_global_daily_limit=limit))
        assert not generation.reserve(str(uuid4()), str(uuid4()))
    finally:
        with Session.begin() as db:
            if original is None:
                db.execute(delete(GenerationUsage).where(GenerationUsage.day == day,
                    GenerationUsage.scope == "global", GenerationUsage.identity == "all"))
            else:
                row = db.scalar(select(GenerationUsage).where(GenerationUsage.day == day,
                    GenerationUsage.scope == "global", GenerationUsage.identity == "all"))
                row.count = original
