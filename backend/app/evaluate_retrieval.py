"""Live retrieval evaluation against seeded synthetic documents.

Requires the real configured embedding model and PostgreSQL. No generated
answers are called, so the metrics make no claim about answer support.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.ai import embed
from app.config import get_settings
from app.db import Session
from app.models import Chunk, Document
from app.retrieval import strong_matches


def main():
    settings = get_settings()
    corpus = Path(__file__).parents[2] / "sample-data" / "evaluation.json"
    if not corpus.exists():
        corpus = Path("/app/evaluation-set.json")
    cases = json.loads(corpus.read_text(encoding="utf-8"))
    results = []
    with Session() as db:
        for case in cases:
            vector = embed([case["question"]])[0]
            distance = Chunk.embedding.cosine_distance(vector)
            matches = db.execute(
                select(Chunk, Document, (1 - distance).label("score"))
                .join(Document, Chunk.document_id == Document.id)
                .where(Document.status == "ready", Document.embedding_model == settings.embedding_model)
                .order_by(distance).limit(settings.top_k)
            ).all()
            gated = strong_matches(matches, settings.minimum_similarity)
            results.append({
                "question": case["question"],
                "expected_source": case["source"],
                "top_matches": [{"document": document.title, "chunk_id": chunk.id, "section": chunk.section, "page": chunk.page_number, "score": round(float(score), 4)} for chunk, document, score in matches],
                "expected_hit_at_k": any(document.title == case["source"] for _, document, _ in matches) if case["source"] else None,
                "expected_hit_after_gate": any(document.title == case["source"] for _, document, _ in gated) if case["source"] else None,
                "retrieval_gate_abstained": not gated,
            })
    supported = [r for r in results if r["expected_source"]]
    unsupported = [r for r in results if not r["expected_source"]]
    report = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "top_k": settings.top_k,
        "minimum_similarity": settings.minimum_similarity,
        "supported_cases": len(supported),
        "unsupported_cases": len(unsupported),
        "retrieval_hit_at_k": sum(r["expected_hit_at_k"] for r in supported) / len(supported),
        "retrieval_hit_after_gate": sum(r["expected_hit_after_gate"] for r in supported) / len(supported),
        "unsupported_retrieval_gate_abstention_rate": sum(r["retrieval_gate_abstained"] for r in unsupported) / len(unsupported),
        "answer_support_rate": None,
        "citation_correctness": None,
        "note": "These are real embedding and pgvector retrieval measurements. Generation and semantic support require the DeepSeek key and human review.",
        "cases": results,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
