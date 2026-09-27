"""Idempotent first-run seed of bundled synthetic knowledge; never replace admin edits."""
import json
import os
from hashlib import sha256
from pathlib import Path
from sqlalchemy import select
from app.config import get_settings
from app.db import Session
from app.embeddings import embed
from app.ingestion import chunk, extract
from app.intents import index_intents
from app.models import Chunk, Document, IntentExample, User


def seed(db):
    settings = get_settings()
    directory = Path("/app/knowledge")
    if not directory.exists():
        directory = Path(__file__).resolve().parents[1] / "knowledge"
    added = 0
    # Seed only an empty knowledge library; deleted documents must stay deleted.
    if db.scalar(select(Document.id).limit(1)) is not None or db.scalar(select(IntentExample.id).limit(1)) is not None:
        return {"documents_added": 0, "reason": "existing_library_preserved"}
    for path in sorted(directory.glob("*.md")):
        data = path.read_bytes()
        passages = chunk(extract(path.name, data), settings.chunk_tokens, settings.overlap_tokens)
        vectors = embed([p.content for p in passages])
        doc = Document(title=path.stem, filename=path.name, mime_type="text/markdown", embedding_model=settings.embedding_model, content_hash=sha256(data).hexdigest())
        db.add(doc)
        db.flush()
        for number, (p, v) in enumerate(zip(passages, vectors, strict=True)):
            db.add(Chunk(document_id=doc.id, chunk_index=number, content=p.content, section=p.section, page_number=p.page, embedding=v))
        added += 1
    db.commit()
    return {"documents_added": added}


if __name__ == "__main__":
    with Session() as db:
        email, password = os.getenv("BOOTSTRAP_ADMIN_EMAIL"), os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if email and password and not db.scalar(select(User).where(User.email == email)):
            if len(password) < 12:
                raise ValueError("Bootstrap admin password must be at least 12 characters")
            from app.auth import passwords
            db.add(User(email=email, password_hash=passwords.hash(password), role="admin"))
            db.commit()
        print(json.dumps({"knowledge": seed(db), "index": index_intents(db)}))
