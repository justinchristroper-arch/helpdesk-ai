import pytest
from app import ai

SOURCES = [{"excerpt": "VPN access requires manager approval and an IT ticket."}]


def test_supported_citation():
    answer, used = ai.validate_answer({"supported": True, "claims": [{"text": "Request manager approval.", "source": 1, "quote": "requires manager approval"}]}, SOURCES)
    assert used == [1]
    assert answer.endswith("[1]")


@pytest.mark.parametrize("claim", [
    {"text": "Approved", "source": 9, "quote": "requires manager approval"},
    {"text": "Approved", "source": 1, "quote": "Invented source text"},
    {"text": "Approved", "source": True, "quote": "requires manager approval"},
    {"text": "", "source": 1, "quote": "requires manager approval"},
])
def test_invalid_citations_fall_back(claim):
    assert ai.validate_answer({"supported": True, "claims": [claim]}, SOURCES) == (ai.FALLBACK, [])


def test_no_context_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(ai, "request", lambda *args: pytest.fail("Provider should not be called"))
    assert ai.generate("What is the CEO salary?", []) == (ai.FALLBACK, [])


def test_embedding_shape_rejected(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(ai, "get_settings", lambda: SimpleNamespace(embedding_model="test"))
    monkeypatch.setattr(ai, "request", lambda *args: {"data": [{"index": 0, "embedding": [0.1]}]})
    with pytest.raises(ai.ProviderError):
        ai.embed(["VPN"])


def test_embedding_response_order(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(ai, "get_settings", lambda: SimpleNamespace(embedding_model="test"))
    monkeypatch.setattr(ai, "request", lambda *args: {"data": [{"index": 1, "embedding": [0.2] * 1536}, {"index": 0, "embedding": [0.1] * 1536}]})
    assert ai.embed(["first", "second"])[0][0] == 0.1
