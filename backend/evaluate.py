"""Run against a seeded live database/provider. Never substitutes canned answers."""
import json
from pathlib import Path

from sqlalchemy import select

from app import ai
from app.config import get_settings
from app.db import Session
from app.models import Chunk, Document


def main():
    settings = get_settings()
    cases = json.loads((Path(__file__).parent.parent / "sample-data/evaluation.json").read_text())
    results = []
    with Session() as db:
        for case in cases:
            vector = ai.embed([case["question"]])[0]
            distance = Chunk.embedding.cosine_distance(vector)
            matches = db.execute(select(Chunk, Document, (1 - distance).label("score")).join(Document, Chunk.document_id == Document.id).where(Document.status == "ready", Document.embedding_model == settings.embedding_model).order_by(distance).limit(settings.top_k)).all()
            context = [{"excerpt": c.content, "title": d.title} for c, d, score in matches if score >= settings.minimum_similarity]
            answer, citations = ai.generate(case["question"], context)
            results.append({**case, "retrieved": [d.title for _, d, _ in matches], "retrieval_hit": any(d.title == case["source"] for _, d, _ in matches) if case["source"] else None, "fallback": not citations, "answer": answer, "citation_count": len(citations), "human_support_review": "pending"})
    supported = [r for r in results if r["source"]]
    unsupported = [r for r in results if not r["source"]]
    report = {"embedding_model": settings.embedding_model, "llm_model": settings.llm_model, "top_k": settings.top_k, "threshold": settings.minimum_similarity, "retrieval_hit_at_k": sum(r["retrieval_hit"] for r in supported) / len(supported), "unsupported_fallback_rate": sum(r["fallback"] for r in unsupported) / len(unsupported), "supported_answer_rate": sum(not r["fallback"] for r in supported) / len(supported), "cases": results, "note": "Citation validation is structural and lexical, not a semantic correctness metric. Human review pending."}
    destination = Path(__file__).parent.parent / "docs/evaluation-results.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved real evaluation results to {destination}")


if __name__ == "__main__":
    main()
