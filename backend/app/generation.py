"""Optional, quota-bound MindRouter synthesis with backend-owned citations."""
import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from dataclasses import dataclass

import httpx
from sqlalchemy import select, text, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import Session
from app.models import Chunk, Document, GenerationUsage


MAX_SYNTHESIS_CHARS = 2400
FACT_MARKER = r"\[F[1-9][0-9]*(?:\s*,\s*F[1-9][0-9]*)*\]"
WRAPPED_MARKER = rf"(?:\*\*{FACT_MARKER}\*\*|\({FACT_MARKER}\)|{FACT_MARKER})"
MARKER_RE = re.compile(rf"(?P<markers>{WRAPPED_MARKER}(?:\s*,?\s*{WRAPPED_MARKER})*)\s*[.!]?\s*$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{5,}\d)(?!\w)")
MULTI_SENTENCE_RE = re.compile(r"[.!?][\"')]*\s+[A-Z0-9]")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "before", "below", "by", "for", "from",
             "if", "in", "into", "is", "it", "of", "on", "or", "that", "the", "their", "them", "then",
             "to", "use", "when", "while", "with", "your", "you"}
TOKEN_ALIASES = {"verify": "check", "verifies": "check", "verified": "check", "connectivity": "network",
                 "reachable": "network", "reach": "contact", "working": "work", "beforehand": "before",
                 "helpdesk": "support", "desk": "support", "device": "laptop", "authentication": "mfa",
                 "required": "require", "requires": "require", "requirements": "require",
                 "allowed": "allow", "allows": "allow", "policies": "policy"}
POLICY_TERMS = {"administrator", "allow", "approval", "approve", "approved", "authorized", "bypass",
                "critical", "deadline", "denied", "disable", "eligible", "exception", "fee", "forbidden",
                "guaranteed", "hr", "immediately", "ineligible", "legal", "manager", "mandatory", "must",
                "permission", "policy", "priority", "prohibited", "rejected", "require", "security",
                "severity", "sla", "status", "supervisor", "urgent", "waiver"}
SENSITIVE_TERMS = POLICY_TERMS | {
    "after", "unless", "without", "not", "never", "no", "cannot", "don't", "doesn't",
    "free", "cost", "dollar", "dollars", "percent", "percentage", "refund", "reimburse",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "fifteen", "twenty", "thirty", "hundred", "thousand", "unlimited",
    "install", "uninstall", "delete", "download", "reinstall", "restart", "reboot",
    "transfer", "pay", "payment", "purchase", "certificate", "registry", "handbook",
    "manual", "contract", "finance", "payroll", "ceo", "director", "override",
    "eleven", "twelve", "thirteen", "fourteen", "sixteen", "seventeen", "eighteen",
    "nineteen", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "million",
    "guide", "protocol",
}


@dataclass(frozen=True)
class ApprovedFact:
    fact_id: str
    text: str
    citation_number: int
    chunk_id: str | None = None
    document_id: str | None = None
    chunk_content: str | None = None


@dataclass
class GroundingResult:
    answer: str | None
    fact_ids: list[str]
    reason: str


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
    referenced_fact_ids: list[str] | None = None

    def diagnostics(self):
        return {"provider": "mindrouter", "state": self.state, "called": self.called,
                "http_status": self.http_status,
                "http_success": 200 <= self.http_status < 300 if self.http_status is not None else None,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "response_model": self.response_model, "finish_reason": self.finish_reason,
                "validation_reason": self.validation_reason, "response_shape": self.response_shape,
                "referenced_fact_ids": self.referenced_fact_ids}


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
        # Formatting only: never persist rejected prose or hidden reasoning.
        "line_shapes": [re.sub(r"[^\[\](),.*!\s]", "x", line)[-160:]
                        for line in content.splitlines()[:20]] if isinstance(content, str) else [],
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
                select(GenerationUsage).where(GenerationUsage.day == day,
                    tuple_(GenerationUsage.scope, GenerationUsage.identity).in_(
                        [(scope, identity) for scope, identity, _ in checks]))).all()}
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


def normalized_tokens(value: str) -> set[str]:
    tokens = set()
    for raw in TOKEN_RE.findall(value.lower()):
        token = TOKEN_ALIASES.get(raw, raw)
        if token not in STOPWORDS:
            tokens.add(token)
    return tokens


def unsupported_values(sentence: str, evidence: str) -> str | None:
    for name, pattern in (("url", URL_RE), ("email", EMAIL_RE), ("phone", PHONE_RE), ("number", NUMBER_RE)):
        allowed = {match.group(0).lower() for match in pattern.finditer(evidence)}
        supplied = {match.group(0).lower() for match in pattern.finditer(sentence)}
        if not supplied.issubset(allowed):
            return f"unsupported_{name}"
    sentence_terms = normalized_tokens(sentence) & SENSITIVE_TERMS
    evidence_terms = normalized_tokens(evidence)
    if not sentence_terms.issubset(evidence_terms):
        return "unsupported_policy_term"
    negations = {"not", "never", "no", "cannot", "don't", "doesn't", "without"}
    if evidence_terms & negations and not normalized_tokens(sentence) & negations:
        return "lost_negation"
    if any(symbol in sentence and symbol not in evidence for symbol in "$£€¥%"):
        return "unsupported_value"
    evidence_words = {word.lower() for word in TOKEN_RE.findall(evidence)}
    for index, word in enumerate(TOKEN_RE.findall(sentence)):
        # Conservative named-entity check; introductory words are not entities.
        if word[0].isupper() and word.lower() not in evidence_words:
            if index == 0 and word.lower() in STOPWORDS | {"first", "next", "please", "confirm", "check", "verify", "ensure"}:
                continue
            return "unsupported_entity"
    return None


def validate_grounded_content(content: str, facts: list[ApprovedFact]) -> GroundingResult:
    """Validate fact markers and conservative deterministic grounding without another model."""
    if not isinstance(content, str) or not content.strip():
        return GroundingResult(None, [], "empty_content")
    if len(content) > MAX_SYNTHESIS_CHARS:
        return GroundingResult(None, [], "content_too_long")
    if any(unicodedata.category(char) in {"Cf", "Cs", "Cc"} and char not in "\n\r\t" for char in content):
        return GroundingResult(None, [], "invalid_unicode")
    # A provider may ignore newlines: split only AFTER complete issued-style
    # marker groups. Uncited sentences within a segment still fail below.
    content = re.sub(rf"({WRAPPED_MARKER}(?:\s*,?\s*{WRAPPED_MARKER})*\s*[.!]?)\s+(?=[A-Za-z0-9•-])",
                     r"\1\n", content)
    allowed = {fact.fact_id: fact for fact in facts}
    rendered, referenced = [], []
    for raw_line in content.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if not line:
            continue
        match = MARKER_RE.search(line)
        if not match:
            reason = "malformed_fact_marker" if "[" in line or "]" in line else "sentence_without_fact_id"
            return GroundingResult(None, referenced, reason)
        sentence = line[:match.start()].strip()
        if (not sentence or "[" in sentence or "]" in sentence or MULTI_SENTENCE_RE.search(sentence)
                or sentence.count("**") % 2 or sentence.count("(") != sentence.count(")")):
            return GroundingResult(None, referenced, "malformed_sentence")
        fact_ids = re.findall(r"F[1-9][0-9]*", match.group("markers"))
        referenced.extend(fact_ids)
        if len(set(fact_ids)) != len(fact_ids) or any(fact_id not in allowed for fact_id in fact_ids):
            return GroundingResult(None, referenced, "unknown_or_duplicate_fact_id")
        evidence = " ".join(allowed[fact_id].text for fact_id in fact_ids)
        unsupported = unsupported_values(sentence, evidence)
        if unsupported:
            return GroundingResult(None, referenced, unsupported)
        sentence_tokens, evidence_tokens = normalized_tokens(sentence), normalized_tokens(evidence)
        overlap = sentence_tokens & evidence_tokens
        if len(overlap) < 2 or (sentence_tokens and len(overlap) / len(sentence_tokens) < 0.55):
            return GroundingResult(None, referenced, "insufficient_fact_overlap")
        if any(len(sentence_tokens & normalized_tokens(allowed[fact_id].text)) < 2 for fact_id in fact_ids):
            return GroundingResult(None, referenced, "unrelated_fact_reference")
        citations = []
        for fact_id in fact_ids:
            citation = allowed[fact_id].citation_number
            if citation not in citations:
                citations.append(citation)
        rendered.append(f"{sentence} [{','.join(str(item) for item in citations)}]")
    if not rendered:
        return GroundingResult(None, referenced, "empty_content")
    cited_sources = {allowed[fact_id].citation_number for fact_id in referenced if fact_id in allowed}
    if cited_sources != {fact.citation_number for fact in facts}:
        return GroundingResult(None, referenced, "incomplete_source_coverage")
    return GroundingResult("\n".join(rendered), referenced, "passed")


def evidence_is_active(facts: list[ApprovedFact]) -> bool:
    """Recheck that every model-visible fact still belongs to an active retrieved chunk."""
    if any(not fact.chunk_id or not fact.document_id for fact in facts):
        return False
    try:
        with Session() as db:
            for fact in facts:
                chunk = db.get(Chunk, fact.chunk_id)
                document = db.get(Document, fact.document_id)
                if (not chunk or not document or document.status != "ready" or
                        chunk.document_id != document.id or chunk.content != fact.chunk_content or
                        fact.text not in chunk.content):
                    return False
        return True
    except SQLAlchemyError:
        return False


def synthesize(question: str, result, user_id: str, ip: str) -> SynthesisResult:
    """One MindRouter call paraphrases approved facts with backend-owned citations."""
    settings = get_settings()
    key = settings.mindrouter_api_key.get_secret_value() if settings.mindrouter_api_key else ""
    if not key:
        return SynthesisResult(None, "disabled")
    if not reserve(user_id, ip):
        return SynthesisResult(None, "quota_or_storage")
    facts = []
    for source_number, (chunk, document, _, source_facts) in enumerate(result.sources, 1):
        for fact in source_facts:
            facts.append(ApprovedFact(f"F{len(facts) + 1}", fact, source_number,
                                      getattr(chunk, "id", None), getattr(document, "id", None),
                                      getattr(chunk, "content", None)))
    payload = {
        "model": settings.mindrouter_model,
        "max_tokens": settings.mindrouter_max_output_tokens,
        "messages": [
            {"role": "system", "content":
             "You are rewriting approved IT facts into a concise user-facing answer. Use only the approved facts "
             "below. You may paraphrase naturally, but do not introduce requirements, numbers, steps, exceptions, "
             "causes, contacts, or policy claims. Return one factual sentence per line, with no heading or bullets. "
             "End every line with its supporting fact IDs exactly like [F1] or [F2,F3]. Use only provided IDs. "
             "If the approved facts are insufficient, say so without inventing details."},
            {"role": "user", "content": "Question: " + question + "\nApproved facts:\n" +
             "\n".join(f"{fact.fact_id}: {fact.text}" for fact in facts)},
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
        if not isinstance(data, dict):
            raise ValueError("Invalid response object")
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
        if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
            return SynthesisResult(None, "invalid_response", called=True, http_status=status,
                                   validation_reason="invalid_message_shape", response_shape=shape)
        finish_reason = choice.get("finish_reason")
        if finish_reason != "stop":
            return SynthesisResult(None, "invalid_response", called=True, http_status=status,
                                   input_tokens=input_tokens, output_tokens=output_tokens,
                                   reasoning_tokens=reasoning_tokens, response_model=response_model,
                                   finish_reason=finish_reason, validation_reason="unsupported_finish_reason",
                                   response_shape=shape)
        grounded = validate_grounded_content(choice["message"]["content"], facts)
        if not grounded.answer:
            return SynthesisResult(None, "invalid_response", called=True, http_status=status,
                                   input_tokens=input_tokens, output_tokens=output_tokens,
                                   reasoning_tokens=reasoning_tokens, response_model=response_model,
                                   finish_reason=finish_reason, validation_reason=grounded.reason,
                                   response_shape=shape, referenced_fact_ids=grounded.fact_ids)
        if not evidence_is_active(facts):
            return SynthesisResult(None, "invalid_response", called=True, http_status=status,
                                   input_tokens=input_tokens, output_tokens=output_tokens,
                                   reasoning_tokens=reasoning_tokens, response_model=response_model,
                                   finish_reason=finish_reason, validation_reason="inactive_evidence",
                                   response_shape=shape, referenced_fact_ids=grounded.fact_ids)
        answer = "Based on the current IT knowledge base:\n\n" + grounded.answer
        return SynthesisResult(answer, "used", called=True, http_status=status,
                               input_tokens=input_tokens, output_tokens=output_tokens,
                               reasoning_tokens=reasoning_tokens, response_model=response_model,
                               finish_reason=finish_reason, validation_reason="passed",
                               response_shape=shape, referenced_fact_ids=grounded.fact_ids)
    except httpx.HTTPStatusError as exc:
        return SynthesisResult(None, f"provider_http_{exc.response.status_code}", True,
                               exc.response.status_code, validation_reason="http_error_before_validation",
                               response_shape=sanitized_error_shape(exc.response))
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return SynthesisResult(None, "provider_failure", called=True, http_status=status,
                               input_tokens=input_tokens, output_tokens=output_tokens,
                               reasoning_tokens=reasoning_tokens, response_model=response_model)
