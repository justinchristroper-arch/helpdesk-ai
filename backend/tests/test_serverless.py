import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from app.client_ip import client_ip
from app.db import get_db
from server import app, backend_app


def request(headers):
    return Request({"type": "http", "client": ("127.0.0.2", 1234),
                    "headers": [(k.encode(), v.encode()) for k, v in headers.items()]})


def test_forwarded_header_ignored_outside_vercel(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    assert client_ip(request({"x-vercel-forwarded-for": "198.51.100.1"})) == "127.0.0.2"


@pytest.mark.parametrize("value,expected", [
    ("198.51.100.1", "198.51.100.1"), ("2001:db8::1", "2001:db8::1"),
    ("", "unknown-vercel-client"), ("bad", "unknown-vercel-client"),
    ("198.51.100.1, 198.51.100.2", "unknown-vercel-client"),
])
def test_vercel_ip_metadata(monkeypatch, value, expected):
    monkeypatch.setenv("VERCEL", "1")
    assert client_ip(request({"x-vercel-forwarded-for": value,
                              "x-forwarded-for": "192.0.2.3"})) == expected


def test_mounted_api_routes_and_docs():
    class DB:
        def execute(self, *args):
            pass
    backend_app.dependency_overrides[get_db] = lambda: DB()
    try:
        client = TestClient(app)
        assert client.get("/api/health").status_code == 200
        assert client.get("/health").status_code == 404
        assert client.get("/api/docs").status_code == 200
        assert '/api/openapi.json' in client.get("/api/docs").text
        assert client.get("/api/unknown").status_code == 404
    finally:
        backend_app.dependency_overrides.clear()
