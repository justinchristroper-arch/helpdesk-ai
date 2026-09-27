import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")

from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from app.auth import admin, current_user
from app.models import User


def fake_db():
    yield None


def test_unauthenticated_and_role_guards():
    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        assert client.get("/conversations").status_code == 401
        app.dependency_overrides[current_user] = lambda: User(id="employee", role="employee", email="demo@example.test")
        assert client.get("/analytics").status_code == 403
        assert client.post("/documents", files={"file": ("x.txt", b"policy")}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_empty_question_rejected_before_provider():
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[current_user] = lambda: User(id="employee", role="employee")
    try:
        client = TestClient(app)
        assert client.post("/chat", json={"question": " "}).status_code == 422
        assert client.post("/chat", json={"question": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_cors_exact_origin():
    client = TestClient(app)
    allowed = client.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    blocked = client.options("/chat", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
