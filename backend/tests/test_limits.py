from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app import limits
from app.limits import limit


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    rows = {}
    clock = [1000.0]
    class DB:
        def execute(self, *args):
            pass
        def scalar(self, *args):
            return clock[0]
        def get(self, model, identity):
            return rows.get(identity)
        def add(self, row):
            rows[row.identity] = row
    @contextmanager
    def begin():
        yield DB()
    monkeypatch.setattr(limits, "Session", SimpleNamespace(begin=begin))
    return rows, clock


def test_excess_requests_are_rejected():
    limit("test-unique-user", 1)
    with pytest.raises(HTTPException) as exc:
        limit("test-unique-user", 1)
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "60"


def test_sliding_window_expires_and_isolates_users(storage):
    rows, clock = storage
    limit("first", 1)
    limit("second", 1)
    clock[0] += 60
    limit("first", 1)
    assert len(rows) == 2
    assert all(len(row.events) == 1 for row in rows.values())
