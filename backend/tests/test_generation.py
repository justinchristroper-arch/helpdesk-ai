"""Optional synthesis cannot introduce facts, citations or unbounded API calls."""
import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
import json
from types import SimpleNamespace

import httpx
import pytest

from app import generation
from app.config import Settings


def approved_facts():
    return [
        generation.ApprovedFact("F1", "Check that your phone has network access and automatic time enabled.", 1),
        generation.ApprovedFact("F2", "Contact IT for an MFA reset if the authenticator is unavailable.", 1),
        generation.ApprovedFact("F3", "IT verifies identity before resetting enrollment.", 1),
        generation.ApprovedFact("F4", "Use an approved managed laptop for remote work.", 2),
        generation.ApprovedFact("F5", "Confirm MFA and test VPN access before remote work.", 2),
    ]


def sample_answer():
    sources = [
        (SimpleNamespace(id="chunk-1", content="Contact IT for MFA reset."),
         SimpleNamespace(id="doc-1"), 0.9, ["Contact IT for MFA reset."]),
        (SimpleNamespace(id="chunk-2", content="Use a trusted network."),
         SimpleNamespace(id="doc-2"), 0.8, ["Use a trusted network."]),
    ]
    return SimpleNamespace(outcome="answered", sources=sources)


def settings(key="test-key"):
    return Settings(_env_file=None, jwt_secret="test-secret-with-at-least-32-characters", mindrouter_api_key=key,
                    mindrouter_base_url="https://api.mindrouter.io/v1", mindrouter_model="openai/gpt-4.1-nano")


def fake_http(monkeypatch, content, finish_reason="stop", status=200, error=None):
    calls = []
    original_client = httpx.Client

    def send(request):
        payload = json.loads(request.content)
        calls.append(payload)
        body = error or {"model": "openai/gpt-4.1-nano", "usage": {"prompt_tokens": 51, "completion_tokens": 17,
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


def test_exact_approved_wording_is_accepted():
    result = generation.validate_grounded_content(
        "Check that your phone has network access and automatic time enabled. [F1]", approved_facts()[:1])
    assert result.reason == "passed" and result.fact_ids == ["F1"]
    assert result.answer.endswith("[1]")


def test_legitimate_paraphrase_is_accepted():
    result = generation.validate_grounded_content(
        "First, verify that your phone has connectivity and automatic time enabled. [F1]", approved_facts()[:1])
    assert result.reason == "passed"


def test_valid_multi_fact_sentence_and_public_citation_conversion():
    result = generation.validate_grounded_content(
        "Use an approved managed laptop and check MFA and VPN access before remote work. [F4,F5]",
        approved_facts()[3:])
    assert result.reason == "passed" and result.fact_ids == ["F4", "F5"]
    assert result.answer.endswith("[2]") and "F4" not in result.answer


@pytest.mark.parametrize(("content", "reason"), [
    ("Check your phone network. [F9]", "unknown_or_duplicate_fact_id"),
    ("Check your phone network.", "sentence_without_fact_id"),
    ("IT will reset MFA within 15 minutes. [F2]", "unsupported_number"),
    ("Get manager approval before contacting IT for an MFA reset. [F2]", "unsupported_policy_term"),
    ("Visit https://support.invalid for an MFA reset. [F2]", "unsupported_url"),
    ("Email reset@example.invalid for an MFA reset. [F2]", "unsupported_email"),
    ("Call +1 555 123 4567 for an MFA reset. [F2]", "unsupported_phone"),
    ("Check your phone network. [F1;F2]", "malformed_fact_marker"),
    ("Check your phone network. Then contact IT. [F1]", "malformed_sentence"),
    ("", "empty_content"),
    ("x" * (generation.MAX_SYNTHESIS_CHARS + 1), "content_too_long"),
])
def test_invalid_grounded_content_is_rejected(content, reason):
    result = generation.validate_grounded_content(content, approved_facts())
    assert result.answer is None and result.reason == reason


def test_synthesis_accepts_paraphrases_and_keeps_backend_citations(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    monkeypatch.setattr(generation, "evidence_is_active", lambda facts: True)
    calls = fake_http(monkeypatch, "Contact IT to reset MFA. [F1]\nUse a trusted network. [F2]")
    result = generation.synthesize("What should I do?", sample_answer(), "user", "127.0.0.1")
    assert result.state == "used"
    assert result.answer.endswith("Contact IT to reset MFA. [1]\nUse a trusted network. [2]")
    assert result.referenced_fact_ids == ["F1", "F2"]
    assert result.diagnostics()["http_success"] is True
    assert (result.input_tokens, result.output_tokens, result.reasoning_tokens) == (51, 17, 0)
    assert result.validation_reason == "passed"
    assert result.response_shape["content_type"] == "str"
    assert len(calls) == 1 and calls[0]["max_tokens"] == 300
    assert set(calls[0]) == {"model", "max_tokens", "messages"}
    assert calls[0]["model"] == "openai/gpt-4.1-nano"
    assert "temperature" not in calls[0]
    assert "response_format" not in calls[0]
    assert "tools" not in calls[0] and "reasoning_effort" not in calls[0] and "thinking" not in calls[0]
    assert calls[0]["messages"][0]["content"].startswith("You are rewriting approved IT facts")
    assert "If the approved facts are insufficient" in calls[0]["messages"][0]["content"]
    assert "Approved facts:\nF1: Contact IT for MFA reset." in calls[0]["messages"][1]["content"]


def test_invalid_synthesis_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    calls = fake_http(monkeypatch, "Use the emergency policy. [F9]")
    result = generation.synthesize("Question", sample_answer(), "user", "ip")
    assert result.answer is None and result.state == "invalid_response"
    assert result.validation_reason == "unknown_or_duplicate_fact_id"
    assert len(calls) == 1


def test_inactive_evidence_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    monkeypatch.setattr(generation, "evidence_is_active", lambda facts: False)
    calls = fake_http(monkeypatch, "Contact IT for MFA reset. [F1]\nUse a trusted network. [F2]")
    result = generation.synthesize("Question", sample_answer(), "user", "ip")
    assert result.answer is None and result.validation_reason == "inactive_evidence" and len(calls) == 1


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


def test_complete_grounded_answer_at_token_limit_remains_safe(monkeypatch):
    monkeypatch.setattr(generation, "get_settings", lambda: settings())
    monkeypatch.setattr(generation, "reserve", lambda *args: True)
    monkeypatch.setattr(generation, "evidence_is_active", lambda facts: True)
    calls = fake_http(monkeypatch,
                      "Contact IT for MFA reset. [F1]\nUse a trusted network. [F2]", finish_reason="length")
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
