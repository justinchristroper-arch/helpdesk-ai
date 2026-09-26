import pytest
from fastapi import HTTPException
from app.limits import limit


def test_excess_requests_are_rejected():
    limit("test-unique-user", 1)
    with pytest.raises(HTTPException) as exc:
        limit("test-unique-user", 1)
    assert exc.value.status_code == 429
