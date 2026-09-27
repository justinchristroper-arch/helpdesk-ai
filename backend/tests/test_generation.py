"""Optional synthesis cannot introduce facts, citations or unbounded API calls."""
import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
import json
from types import SimpleNamespace

import httpx
import pytest

from app import generation
from app.config import Settings


def sample_answer():
    sources = [
        (SimpleNamespace(content="Contact IT for MFA reset."), SimpleNamespace(), 0.9, ["Contact IT for MFA reset."]),
        (SimpleNamespace(content="Use a trusted network."), SimpleNamespace(), 0.8, ["Use a trusted network."]),
    ]
    return SimpleNamespace(outcome="answered", sources=sources)


def settings(key="test-key"):
    return Settings(_env_file=None, jwt_secret="test-secret-with-at-least-32-characters", mindrouter_api_key=key,
                    mindrouter_base_url="https://api.mindrouter.io/v1", mindrouter_model="zai/glm-5.3-flash")


def fake_http(monkeypatch, content, finish_reason="stop", status=200, error=None):
    calls = []
    original_client = httpx.Client

    def send(request):
        payload = json.loads(request.content)
        calls.append(payload)
        body = error or {"model": "zai/glm-5.3-flash", "usage": {"prompt_tokens": 51, "completion_tokens": 17,
                         "completion_tokens_details": {"reasoning_tokens": 0}},
                         "choices": [{"finish_reason": finish_reason, "message": {"content": content}}]}
        return httpx.Response(status, json=body)

    class Client:
        def __init__(self, **kwargs):
            self.client = original_client(transport=httpx.MockTransport(send))

        def __enter__(self):
            return self.client.__enter__()

        def __exit__(self, *args):
            return self.client.__exit__(*args)

    monkeypatch.setattr(generation.httpx, "Client", Client)
    return calls


def test_synthesis_uses_only_verbatim_source_facts_and_backend_citations(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, "- Use a trusted network. [2]\n- Contact IT for MFA reset. [1]")
    result = generation.synthesize("What should I do?", sample_answer(), "user", "127.0.0.1")
    assert result.state == "used" and result.answer.endswith("• Use a trusted network. [2]\n• Contact IT for MFA reset. [1]")
    assert result.diagnostics()["http_success"] is True
    assert (result.input_tokens, result.output_tokens, result.reasoning_tokens) == (51, 17, 0)
    assert result.validation_reason == "passed"
    assert result.response_shape["content_type"] == "str"
    assert len(calls) == 1 and calls[0]["max_tokens"] == 300
    assert set(calls[0]) == {"model", "max_tokens", "messages"}
    assert calls[0]["model"] == "zai/glm-5.3-flash"
    assert "temperature" not in calls[0]
    assert "response_format" not in calls[0]
    assert "tools" not in calls[0] and "reasoning_effort" not in calls[0] and "thinking" not in calls[0]
    assert calls[0]["messages"][0]["content"].startswith("Answer only from the approved facts below.")
    assert "Approved facts:\n- Contact IT for MFA reset. [1]" in calls[0]["messages"][1]["content"]


@pytest.mark.parametrize("content", [
    "Invented policy [1]\nUse a trusted network. [2]",
    "Contact IT for MFA reset. [1]",
    "Contact IT for MFA reset. [1]\nContact IT for MFA reset. [1]\nUse a trusted network. [2]",
    "Contact IT for MFA reset. [3]\nUse a trusted network. [2]",
    "not approved",
])
def test_invalid_synthesis_falls_back_without_using_model_text(monkeypatch, content):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, content)
    result = generation.synthesize("Question", sample_answer(), "user", "ip")
    assert result.answer is None and result.state in {"invalid_response", "provider_failure"}
    if result.state == "invalid_response":
        assert result.validation_reason == "content_not_approved_facts"
    assert len(calls) == 1


def test_disabled_or_quota_skips_network(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings(""))
    assert generation.synthesize("Q", sample_answer(), "u", "ip").state == "disabled"
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: False)
    assert generation.synthesize("Q", sample_answer(), "u", "ip").state == "quota_or_storage"


def test_provider_http_failure_is_single_call_and_fallback(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, "{}", status=402,
                      error={"error": {"type": "billing_error", "code": "insufficient_balance", "message": "private detail"}})
    result = generation.synthesize("Q", sample_answer(), "u", "ip")
    assert result.state == "provider_http_402" and result.called and result.http_status == 402
    assert result.validation_reason == "http_error_before_validation"
    assert result.response_shape == {"root_type": "dict", "root_keys": ["error"],
        "error_type": "billing_error", "error_code": "insufficient_balance",
        "error_keys": ["code", "message", "type"], "message_present": True, "message_length": 14}
    assert "private detail" not in json.dumps(result.diagnostics())
    assert len(calls) == 1


def test_complete_approved_facts_at_token_limit_remain_safe(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch,
                      "Contact IT for MFA reset. [1]\nUse a trusted network. [2]", finish_reason="length")
    result = generation.synthesize("Q", sample_answer(), "u", "ip")
    assert result.state == "used" and result.finish_reason == "length" and len(calls) == 1


def test_only_multisource_answer_eligible():
    result = sample_answer()
    assert generation.should_synthesize(result, "What should I do?")
    result.sources = result.sources[:1]
    assert not generation.should_synthesize(result, "What should I do?")
    result.sources = [(result.sources[0][0], result.sources[0][1], .9,
                       ["Contact IT for MFA reset.", "Use a trusted network."])]
    assert generation.should_synthesize(result, "I am currently far from the office and need to get my broken sign in app fixed before I can work; what steps should I follow?")
    result.sources = sample_answer().sources
    result.outcome = "fallback"
    assert not generation.should_synthesize(result, "What should I do?")
