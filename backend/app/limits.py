"""PostgreSQL sliding-window limits shared by every serverless instance."""
from hashlib import sha256
from math import ceil

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text

from app.db import Session
from app.models import RequestLimit


def limit(key: str, maximum: int, window: int = 60):
    identity = sha256(key.encode()).hexdigest()
    lock_id = int.from_bytes(bytes.fromhex(identity)[:8], "big", signed=True)
    retry_after = None
    with Session.begin() as db:
        # Protect the first insert as well as existing rows across instances.
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        current = float(db.scalar(select(func.extract("epoch", func.clock_timestamp()))))
        row = db.get(RequestLimit, identity)
        events = [stamp for stamp in (row.events if row else []) if stamp > current - window]
        if len(events) >= maximum:
            retry_after = max(1, ceil(events[0] + window - current))
        else:
            events.append(current)
            if row is None:
                row = RequestLimit(identity=identity)
                db.add(row)
            row.events = events
            row.expires_at = current + window
        # Expired counters only; no user/content rows are touched.
        expired = (select(RequestLimit.identity).where(RequestLimit.expires_at <= current)
                   .limit(100).with_for_update(skip_locked=True))
        db.execute(delete(RequestLimit).where(RequestLimit.identity.in_(expired)))
    if retry_after is not None:
        raise HTTPException(429, "Too many requests. Please wait a minute.",
                            headers={"Retry-After": str(retry_after)})
