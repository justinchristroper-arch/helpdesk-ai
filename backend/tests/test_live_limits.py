"""Real cross-session concurrency check; never calls an external LLM."""
import os
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete
from app.db import Session
from app.limits import limit
from app.models import RequestLimit

pytestmark = pytest.mark.skipif(os.getenv("LIVE_SEMANTIC") != "1",
                                reason="Requires migrated PostgreSQL")


def test_concurrent_instances_share_request_limit():
    key = "test-concurrent:" + uuid4().hex
    identity = sha256(key.encode()).hexdigest()
    def attempt(_):
        try:
            limit(key, 3)
            return 200
        except HTTPException as exc:
            return exc.status_code
    try:
        with ThreadPoolExecutor(max_workers=6) as workers:
            outcomes = list(workers.map(attempt, range(10)))
        assert outcomes.count(200) == 3
        assert outcomes.count(429) == 7
        with Session() as db:
            assert len(db.get(RequestLimit, identity).events) == 3
    finally:
        with Session.begin() as db:
            db.execute(delete(RequestLimit).where(RequestLimit.identity == identity))
