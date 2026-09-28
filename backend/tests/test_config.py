"""Database settings select psycopg3 without leaking credentials."""
import pytest
from pydantic import ValidationError

from app.config import Settings


BASE = {"_env_file": None, "jwt_secret": "test-secret-with-at-least-32-characters"}


@pytest.mark.parametrize("prefix", ["postgresql://", "postgres://"])
def test_neon_style_url_uses_psycopg3_and_preserves_ssl(prefix):
    settings = Settings(**BASE, database_url=prefix + "demo:encoded%40password@host.example/neondb?sslmode=require")
    assert settings.database_url == (
        "postgresql+psycopg://demo:encoded%40password@host.example/neondb?sslmode=require")


def test_explicit_psycopg3_url_is_unchanged():
    url = "postgresql+psycopg://demo:password@host.example/neondb?sslmode=verify-full"
    assert Settings(**BASE, database_url=url).database_url == url


def test_invalid_database_scheme_fails_without_echoing_secret():
    secret = "must-not-appear-in-errors"
    with pytest.raises(ValidationError) as error:
        Settings(**BASE, database_url=f"mysql://user:{secret}@host.example/db")
    assert secret not in str(error.value)
