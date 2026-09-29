"""Versioned, reviewed semantic examples and exact source-backed facts."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import delete, select, update
from app.config import get_settings
from app.embeddings import embed
from app.models import IntentExample

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "intents.json"


@lru_cache(maxsize=1)
def dataset():
    raw = DATA_PATH.read_bytes()
    data = json.loads(raw)
    ids = set()
    for item in data["intents"]:
        if item["intent_id"] in ids or not item["evidence"]:
            raise ValueError("Duplicate intent or missing evidence")
        ids.add(item["intent_id"])
        for source in item["evidence"]:
            if not source["facts"] or any(len(fact) < 12 for fact in source["facts"]):
                raise ValueError("Approved facts must contain substantive exact source text")
    # Git may check out this JSON with CRLF on Windows, while Vercel uses LF.
    # Keep the index version identical across both environments.
    canonical = raw.replace(b"\r\n", b"\n")
    return {i["intent_id"]: i for i in data["intents"]}, hashlib.sha256(canonical).hexdigest()


def index_intents(db):
    intents, digest = dataset()
    model = get_settings().embedding_model
    existing = set(db.scalars(select(IntentExample.id)))
    pending, keep = [], set()
    for ident, item in intents.items():
        for negative, texts in ((False, [item["canonical_question"], *item["paraphrases"]]), (True, item["negative_examples"])):
            for content in texts:
                key = hashlib.sha256(f"{ident}|{negative}|{model}|{content}".encode()).hexdigest()
                keep.add(key)
                if key not in existing:
                    pending.append(dict(id=key, intent_id=ident, content=content, negative=negative, embedding_model=model, dataset_hash=digest))
    if existing & keep:
        db.execute(update(IntentExample).where(IntentExample.id.in_(existing & keep)).values(dataset_hash=digest))
    if pending:
        for record, vector in zip(pending, embed([r["content"] for r in pending]), strict=True):
            db.add(IntentExample(**record, embedding=vector))
    stale = set(existing) - keep
    if stale:
        db.execute(delete(IntentExample).where(IntentExample.id.in_(stale)))
    db.commit()
    return {"intents": len(intents), "examples": len(keep), "new_embeddings": len(pending), "dataset_hash": digest}


if __name__ == "__main__":
    from app.db import Session
    with Session() as db:
        print(json.dumps(index_intents(db)))
