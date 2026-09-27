"""Explainable semantic matching and exact-fact evidence composition; no generation."""
import re
from dataclasses import dataclass, field
from hashlib import sha256

from sqlalchemy import func, select
from app.config import get_settings
from app.embeddings import embed
from app.intents import dataset
from app.models import Chunk, Document, IntentExample

VERSION = "evidence-v2"
FALLBACK = ("I couldn't find enough information in the current IT knowledge base to answer that reliably. "
            "Try asking about VPN access, MFA, laptop issues, software installation, database access, "
            "account unlocks, remote work IT procedures, or incident SLAs.")


@dataclass
class Answer:
    content: str = FALLBACK
    outcome: str = "fallback"
    intent_id: str | None = None
    sources: list = field(default_factory=list)
    clarification: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    context: dict | None = None


def normalize(query):
    query = re.sub(r"\s+", " ", query.lower().replace("’", "'")).strip()
    typos = {"vpm": "vpn", "laptpo": "laptop", "authentcator": "authenticator", "softwre": "software", "unlok": "unlock", "conection": "connection", "acess": "access"}
    return re.sub(r"\b\w+\b", lambda m: typos.get(m[0], m[0]), query)


def resolve_query(query, context):
    normalized = normalize(query)
    if not context or not context.get("active_intent"):
        return normalized, False
    intents, _ = dataset()
    active = intents.get(context["active_intent"])
    if not active:
        return normalized, False
    explicit = any(re.search(r"\b" + re.escape(k) + r"\b", normalized)
                   for item in intents.values() for k in item["keywords"] if k not in {"home", "connect", "reset", "write"})
    followup = bool(re.search(r"\b(it|that|this|those|then|next|approval|requirements|afterwards|beforehand)\b", normalized))
    if len(normalized.split()) <= 15 and followup and not explicit:
        generic = normalized in {"what should i do next?", "what should i check beforehand?", "what are the requirements?"}
        return normalize((active["canonical_question"] if generic else active["topic"]) + ": " + normalized), True
    return normalized, False


def rank_intents(db, vector):
    _, digest = dataset()
    score = 1 - IntentExample.embedding.cosine_distance(vector)
    rows = db.execute(select(IntentExample.intent_id, IntentExample.negative, func.max(score))
        .where(IntentExample.embedding_model == get_settings().embedding_model, IntentExample.dataset_hash == digest)
        .group_by(IntentExample.intent_id, IntentExample.negative)).all()
    positives = sorted([(i, float(s)) for i, negative, s in rows if not negative], key=lambda x: (-x[1], x[0]))
    negatives = {i: float(s) for i, negative, s in rows if negative}
    return positives, negatives


def compose(intent, sources, query):
    """Only verified verbatim facts are factual content; presentation is deterministic."""
    intros = ["Here's the documented guidance:", "Based on the current IT knowledge base:", "The documented process is:"]
    intro = intros[int(sha256(normalize(query).encode()).hexdigest()[:8], 16) % len(intros)]
    sections = [intro]
    for number, (chunk, document, score, facts) in enumerate(sources, 1):
        if not all(fact in chunk.content for fact in facts):
            raise ValueError("Fact is not supported by the retrieved source")
        ordered = intent["answer_type"] in {"procedure", "troubleshooting", "checklist"}
        lines = [f"{index}. {fact} [{number}]" if ordered else f"• {fact} [{number}]" for index, fact in enumerate(facts, 1)]
        sections.append(f"{chunk.section or document.title}\n" + "\n".join(lines))
    return "\n\n".join(sections)


def answer(db, query, context=None):
    settings = get_settings()
    intents, _ = dataset()
    resolved, used_context = resolve_query(query, context)
    vector = embed([resolved])[0]
    ranked, negatives = rank_intents(db, vector)
    ranked = [(i,s) for i,s in ranked if all(any(term in resolved for term in group) for group in intents[i].get("required_groups", [])) and not any(re.search(p, resolved) for p in intents[i].get("exclude_patterns", []))]
    if ranked:
        preferred = [(i,s) for i,s in ranked if ranked[0][1]-s <= settings.specificity_window and any(re.search(p, resolved) for p in intents[i].get("prefer_patterns", []))]
        if preferred:
            ranked = preferred + [(i,s) for i,s in ranked if i not in {p[0] for p in preferred}]
    diagnostic = {"resolved_query": resolved, "used_context": used_context, "ranking": [{"intent": i, "score": round(s, 6)} for i, s in ranked[:3]], "gate": "no_index"}
    result = Answer(diagnostics=diagnostic)
    if not ranked:
        return result
    ident, top = ranked[0]
    item = intents[ident]
    second = ranked[1][1] if len(ranked) > 1 else 0
    negative = negatives.get(ident, 0)
    diagnostic.update(intent_score=top, margin=top-second, negative_score=negative)
    # A known negative defeats a nearby positive; the FAQ path never bypasses it.
    if negative >= top - settings.negative_margin:
        diagnostic["gate"] = "negative_example"
        return result
    keyword = any(re.search(r"\b"+re.escape(k)+r"\b", resolved) for k in item["keywords"])
    if any(re.search(p, resolved) for p in item.get("unsupported_patterns", [])):
        diagnostic["gate"] = "unsupported_facet"
        return result
    generic_access = (bool(re.search(r"\baccess\b", resolved)) and not any(k in resolved for k in ["vpn", "database", "software", "account", "remote", "network"])) or resolved in {"vpn", "mfa", "database", "software", "laptop", "account", "remote work"}
    if generic_access and top >= settings.intent_minimum:
        options = [intents[i] for i,s in ranked[:3]]
        result.outcome = "clarification"
        result.clarification = [{"intent_id": i["intent_id"], "topic": i["topic"], "question": i["canonical_question"]} for i in options]
        result.content = "Which topic do you mean?\n" + "\n".join("• " + i["topic"] for i in options)
        diagnostic["gate"] = "underspecified_access"
        return result
    if top < settings.intent_minimum or (not keyword and top < settings.intent_without_keyword):
        diagnostic["gate"] = "weak_intent"
        return result
    specific = any(re.search(p, resolved) for p in item.get("prefer_patterns", []))
    margin = settings.short_query_margin if len(resolved.split()) <= 3 else settings.intent_margin
    if top - second < margin and top < settings.faq_similarity and not specific:
        options = [intents[i] for i, s in ranked[:3] if top-s < margin]
        result.outcome = "clarification"
        result.clarification = [{"intent_id": i["intent_id"], "topic": i["topic"], "question": i["canonical_question"]} for i in options]
        result.content = "I found more than one possible topic. Are you asking about:\n" + "\n".join("• " + i["topic"] for i in options)
        diagnostic["gate"] = "ambiguous_intents"
        return result
    diagnostic["path"] = "faq" if top >= settings.faq_similarity else "semantic"
    canonical = db.scalar(select(IntentExample).where(IntentExample.intent_id == ident, IntentExample.content == item["canonical_question"], IntentExample.negative.is_(False), IntentExample.embedding_model == settings.embedding_model))
    evidence_vector = canonical.embedding if canonical is not None else vector
    distance = Chunk.embedding.cosine_distance(evidence_vector)
    base = select(Chunk, Document, (1-distance).label("score")).join(Document, Chunk.document_id == Document.id).where(Document.status == "ready", Document.embedding_model == settings.embedding_model)
    # Always retrieve authoritative, current source rows. Broad search is diagnostic
    # on the semantic path; high-confidence FAQs skip that extra query.
    if diagnostic["path"] == "semantic":
        broad = db.execute(base.order_by(distance).limit(settings.top_k)).all()
        diagnostic["retrieved_documents"] = list(dict.fromkeys(d.filename for c, d, s in broad))
    sources, seen = [], set()
    for ref in item["evidence"]:
        candidates = db.execute(base.where(Document.filename == ref["filename"], Chunk.section == ref["section"]).order_by(distance, Document.created_at.desc()).limit(settings.top_k)).all()
        valid = [(c,d,float(s),ref["facts"]) for c,d,s in candidates if s >= settings.evidence_minimum and all(f in c.content for f in ref["facts"])]
        if not valid:
            diagnostic["gate"] = "missing_or_changed_evidence"
            return result
        evidence = valid[0]
        key = normalize(evidence[0].content)
        if key not in seen:
            sources.append(evidence)
            seen.add(key)
    if len(sources) > settings.top_k:
        diagnostic["gate"] = "evidence_limit"
        return result
    diagnostic["gate"] = "accepted"
    result.content = compose(item, sources, query)
    result.outcome, result.intent_id, result.sources = "answered", ident, sources
    result.context = {"active_intent": ident, "active_topic": item["topic"], "recent_documents": [d.id for c,d,s,f in sources], "recent_query": query}
    return result
