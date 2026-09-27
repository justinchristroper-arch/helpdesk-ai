"""Real FastEmbed/pgvector evaluation. Emit measured results, including failures."""
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from app.db import Session
from app.intents import dataset
from app.semantic import answer


def run():
    cases = json.loads((Path(__file__).parents[1] / "data/evaluation.json").read_text())["cases"]
    intents, digest = dataset()
    results = []
    with Session() as db:
        for case in cases:
            start = perf_counter()
            result = answer(db, case["question"], case.get("context"))
            expected = {e["filename"] for e in intents[case["intent"]]["evidence"]} if case["intent"] else set()
            files = {d.filename for c,d,s,f in result.sources}
            ranking = result.diagnostics["ranking"]
            valid = all(all(f in c.content for f in facts) and c.document_id == d.id for c,d,s,facts in result.sources)
            results.append({**case, "actual_outcome": result.outcome, "actual_intent": result.intent_id,
                "intent_top1_correct": bool(ranking and ranking[0]["intent"] == case["intent"]) if case["intent"] else None,
                "intent_top3_hit": any(r["intent"] == case["intent"] for r in ranking) if case["intent"] else None,
                "retrieval_hit": bool(files & expected) if expected else None,
                "all_expected_sources": expected <= files if expected else None,
                "citation_valid": valid if result.sources else None,
                "evidence_supported": valid if result.sources else None,
                "citation_count": len(result.sources), "answer": result.content,
                "milliseconds": round((perf_counter()-start)*1000, 2), "diagnostics": result.diagnostics})
    def metrics(rows):
        supported = [r for r in rows if r["intent"]]
        unsupported = [r for r in rows if r["outcome"] == "fallback"]
        ambiguous = [r for r in rows if r["outcome"] == "clarification"]
        answered = [r for r in rows if r["actual_outcome"] == "answered"]
        followups = [r for r in rows if r["category"] == "followup"]
        def rate(values):
            return {"passed": sum(values), "total": len(values), "rate": sum(values)/len(values) if values else None}
        return {"intent_top1": rate([r["intent_top1_correct"] for r in supported]),
            "intent_top3": rate([r["intent_top3_hit"] for r in supported]),
            "supported_recall": rate([r["actual_outcome"] == "answered" and r["actual_intent"] == r["intent"] for r in supported]),
            "retrieval_hit_at_3": rate([r["retrieval_hit"] for r in supported]),
            "unsupported_rejection": rate([r["actual_outcome"] == "fallback" for r in unsupported]),
            "ambiguity_detection": rate([r["actual_outcome"] == "clarification" for r in ambiguous]),
            "citation_validity": rate([r["citation_valid"] for r in answered]),
            "verbatim_evidence_support": rate([r["evidence_supported"] for r in answered]),
            "followup_resolution": rate([r["actual_intent"] == r["intent"] and r["diagnostics"]["used_context"] for r in followups])}
    return {"measured_at": datetime.now(timezone.utc).isoformat(), "dataset_hash": digest,
        "definitions": {"intent_top1": "First intent after semantic ranking and explicit scope/specificity rules matches expected intent, before evidence gate.",
            "supported_recall": "Expected supported cases answered with expected intent.",
            "retrieval_hit_at_3": "Supported cases with at least one expected document among at most three returned evidence chunks; fallback counts as a miss.",
            "citation_validity": "Answered cases whose citations identify real document/chunk pairs.",
            "verbatim_evidence_support": "Answered cases where every composed fact is an exact substring of its cited chunk; this is not independent semantic entailment assessment.",
            "followup_resolution": "Follow-ups use stored topic and return expected intent."},
        "benchmark_note": "All 80 cases are now inspected regression cases, not blind accuracy estimates. Initial frozen-rule results for the final 16, including two failures, are preserved in evaluation-initial-validation.json.",
        "metrics": metrics(results), "validation_metrics": metrics([r for r in results if r["split"] == "validation"]), "cases": results}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
