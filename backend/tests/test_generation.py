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
                    mindrouter_base_url="https://api.mindrouter.io/v1", mindrouter_model="deepseek/deepseek-flash")


def fake_http(monkeypatch, content, finish_reason="stop", status=200, error=None):
    calls = []
    original_client = httpx.Client

    def send(request):
        payload = json.loads(request.content)
        calls.append(payload)
        body = error or {"model": "deepseek/deepseek-flash", "usage": {"prompt_tokens": 51, "completion_tokens": 17},
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


def test_synthesis_selects_only_source_facts_and_backend_citations(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, '{"fact_ids":["2.1","1.1"]}')
    result = generation.synthesize("What should I do?", sample_answer(), "user", "127.0.0.1")
    assert result.state == "used" and result.answer.endswith("• Use a trusted network. [2]\n• Contact IT for MFA reset. [1]")
    assert result.diagnostics()["http_success"] is True
    assert (result.input_tokens, result.output_tokens) == (51, 17)
    assert result.validation_reason == "passed"
    assert result.response_shape["content_type"] == "str"
    assert len(calls) == 1 and calls[0]["max_tokens"] == 300
    assert calls[0]["model"] == "deepseek/deepseek-flash"
    assert calls[0]["temperature"] == 0
    assert "response_format" not in calls[0]
    assert "tools" not in calls[0] and "reasoning_effort" not in calls[0]


@pytest.mark.parametrize("content", [
    '{"fact_ids":["3.1"]}', '{"fact_ids":["1.1"]}',
    '{"fact_ids":["1.1","1.1","2.1"]}', '{"answer":"invented policy"}', "not json",
])
def test_invalid_synthesis_falls_back_without_using_model_text(monkeypatch, content):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, content)
    result = generation.synthesize("Question", sample_answer(), "user", "ip")
    assert result.answer is None and result.state in {"invalid_response", "provider_failure"}
    if result.state == "invalid_response":
        assert result.validation_reason in {"content_not_fact_ids_json", "invalid_fact_ids"}
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


def test_complete_json_at_token_limit_remains_safe(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, '{"fact_ids":["1.1","2.1"]}', finish_reason="length")
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
