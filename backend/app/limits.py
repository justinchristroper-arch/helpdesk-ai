"""Single-process demo limits. Multi-instance hosting requires shared limits."""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException

_events: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def limit(key: str, maximum: int, window: int = 60):
    current = time.monotonic()
    with _lock:
        expired = [k for k, values in _events.items() if not values or values[-1] <= current - window]
        for old in expired:
            del _events[old]
        values = _events[key]
        while values and values[0] <= current - window:
            values.popleft()
        if len(values) >= maximum:
            raise HTTPException(429, "Too many requests. Please wait a minute.", headers={"Retry-After": str(window)})
        values.append(current)
