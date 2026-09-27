"""Optional, quota-bound MindRouter synthesis with backend-owned citations."""
import hashlib
import re
from datetime import datetime, timezone
from dataclasses import dataclass

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import Session
from app.models import GenerationUsage


@dataclass
class SynthesisResult:
    answer: str | None
    state: str
    called: bool = False
    http_status: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    response_model: str | None = None
    finish_reason: str | None = None
    validation_reason: str | None = None
    response_shape: dict | None = None

    def diagnostics(self):
        return {"provider": "mindrouter", "state": self.state, "called": self.called,
                "http_status": self.http_status,
                "http_success": 200 <= self.http_status < 300 if self.http_status is not None else None,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "response_model": self.response_model, "finish_reason": self.finish_reason,
                "validation_reason": self.validation_reason, "response_shape": self.response_shape}


def sanitized_shape(data, choice=None):
    """Describe response structure without retaining model text or credentials."""
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    reasoning = message.get("reasoning_content") if isinstance(message, dict) else None
    return {
        "root_type": type(data).__name__,
        "root_keys": sorted(data) if isinstance(data, dict) else [],
        "choices_type": type(data.get("choices")).__name__ if isinstance(data, dict) else None,
        "choices_count": len(data.get("choices")) if isinstance(data, dict) and isinstance(data.get("choices"), list) else None,
        "choice_keys": sorted(choice) if isinstance(choice, dict) else [],
        "message_type": type(message).__name__,
        "message_keys": sorted(message) if isinstance(message, dict) else [],
        "content_type": type(content).__name__,
        "content_length": len(content) if isinstance(content, str) else None,
        "content_nonempty": bool(content) if isinstance(content, str) else False,
        "reasoning_type": type(reasoning).__name__,
        "reasoning_length": len(reasoning) if isinstance(reasoning, str) else None,
    }


def sanitized_error_shape(response):
    """Keep only structural/provider codes from an error; never retain its message."""
    try:
        data = response.json()
    except ValueError:
        return {"root_type": "non_json", "body_length": len(response.content)}
    error = data.get("error") if isinstance(data, dict) else None
    return {
        "root_type": type(data).__name__,
        "root_keys": sorted(data) if isinstance(data, dict) else [],
        "error_type": error.get("type") if isinstance(error, dict) and isinstance(error.get("type"), str) else None,
        "error_code": error.get("code") if isinstance(error, dict) and isinstance(error.get("code"), (str, int)) else None,
        "error_keys": sorted(error) if isinstance(error, dict) else [],
        "message_present": isinstance(error.get("message"), str) if isinstance(error, dict) else False,
        "message_length": len(error.get("message")) if isinstance(error, dict) and isinstance(error.get("message"), str) else None,
    }


def reserve(user_id: str, ip: str) -> bool:
    """Count attempts, including failed requests, before any external call."""
    settings = get_settings()
    day = datetime.now(timezone.utc).date()
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()
    checks = (("global", "all", settings.generation_global_daily_limit),
              ("user", user_id, settings.generation_user_daily_limit),
              ("ip", ip_hash, settings.generation_ip_daily_limit))
    try:
        with Session.begin() as db:
            # A single PostgreSQL transaction lock serializes every reservation
            # across processes. Commit happens before the network request.
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 751000000 + day.toordinal()})
            rows = {(r.scope, r.identity): r for r in db.scalars(
                select(GenerationUsage).where(GenerationUsage.day == day)).all()}
            if any(rows.get((scope, identity)) and rows[(scope, identity)].count >= maximum
                   for scope, identity, maximum in checks):
                return False
            for scope, identity, _ in checks:
                row = rows.get((scope, identity))
                if row is None:
                    row = GenerationUsage(day=day, scope=scope, identity=identity, count=0)
                    db.add(row)
                row.count += 1
        return True
    except SQLAlchemyError:
        return False


def should_synthesize(result, question: str) -> bool:
    if result.outcome != "answered" or not result.sources:
        return False
    facts = sum(len(source_facts) for _, _, _, source_facts in result.sources)
    return len(result.sources) > 1 or (len(question.split()) >= 18 and facts >= 2)


def approved_lines(content: str, facts: list[tuple[str, int]]) -> list[tuple[str, int]] | None:
    """Accept only complete, verbatim approved facts with backend-issued markers."""
    allowed = {f"{fact} [{source}]": (fact, source) for fact, source in facts}
    selected = []
    for raw_line in content.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if not line:
            continue
        item = allowed.get(line)
        if item is None or item in selected:
            return None
        selected.append(item)
    if not selected or {source for _, source in selected} != {source for _, source in facts}:
        return None
    return selected


def synthesize(question: str, result, user_id: str, ip: str) -> SynthesisResult:
    """One MindRouter call selects verbatim facts; all displayed facts come from DB."""
    settings = get_settings()
    key = settings.mindrouter_api_key.get_secret_value() if settings.mindrouter_api_key else ""
    if not key:
        return SynthesisResult(None, "disabled")
    if not reserve(user_id, ip):
        return SynthesisResult(None, "quota_or_storage")
    facts = [(fact, source_number)
             for source_number, (_, _, _, source_facts) in enumerate(result.sources, 1)
             for fact in source_facts]
    payload = {
        "model": settings.mindrouter_model,
        "max_tokens": settings.mindrouter_max_output_tokens,
        "messages": [
            {"role": "system", "content":
             "Answer only from the approved facts below. Be concise. Use source markers exactly as provided. "
             "Copy each selected fact verbatim, followed by its source marker. Include at least one fact from "
             "every source. Do not add a preface."},
            {"role": "user", "content": "Question: " + question + "\nApproved facts:\n" +
             "\n".join(f"- {fact} [{source}]" for fact, source in facts)},
        ],
    }
    status, input_tokens, output_tokens, reasoning_tokens, response_model = None, None, None, None, None
    try:
        with httpx.Client(timeout=httpx.Timeout(25, connect=5), trust_env=False) as client:
            response = client.post(settings.mindrouter_base_url.rstrip("/") + "/chat/completions",
                                   headers={"Authorization": f"Bearer {key}"}, json=payload)
            status = response.status_code
            response.raise_for_status()
            data = response.json()
        usage = data.get("usage") or {}
        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int else None
            output_tokens = usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None
            details = usage.get("completion_tokens_details")
            if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int:
                reasoning_tokens = details["reasoning_tokens"]
        response_model = data.get("model") if isinstance(data.get("model"), str) else None
        choice = data["choices"][0]
        shape = sanitized_shape(data, choice)
        finish_reason = choice.get("finish_reason")
        if finish_reason not in {"stop", "length"}:
            return SynthesisResult(None, "invalid_response", True, status, input_tokens, output_tokens,
                                   reasoning_tokens, response_model, finish_reason, "unsupported_finish_reason", shape)
        selected = approved_lines(choice["message"]["content"], facts)
        if selected is None:
            return SynthesisResult(None, "invalid_response", True, status, input_tokens, output_tokens,
                                   reasoning_tokens, response_model, finish_reason,
                                   "content_not_approved_facts", shape)
        answer = "Based on the current IT knowledge base:\n\n" + "\n".join(
            f"• {fact} [{source}]" for fact, source in selected)
        return SynthesisResult(answer, "used", True, status, input_tokens, output_tokens,
                               reasoning_tokens, response_model, finish_reason, "passed", shape)
    except httpx.HTTPStatusError as exc:
        return SynthesisResult(None, f"provider_http_{exc.response.status_code}", True,
                               exc.response.status_code, validation_reason="http_error_before_validation",
                               response_shape=sanitized_error_shape(exc.response))
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return SynthesisResult(None, "provider_failure", True, status, input_tokens, output_tokens,
                               reasoning_tokens, response_model)
