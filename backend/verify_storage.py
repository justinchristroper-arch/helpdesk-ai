"""Verify the actual pgvector column with clearly synthetic fixture vectors.

This proves storage/search wiring, not an embedding provider. Rows are removed
after verification; no real or confidential documents are used.
"""
from sqlalchemy import select, text
from alembic.script import ScriptDirectory
from pathlib import Path

from app.db import Session
from app.models import Chunk, Document


def main():
    vector_a = [1.0] + [0.0] * 383
    vector_b = [0.0, 1.0] + [0.0] * 382
    with Session() as db:
        version = db.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        dimension = db.scalar(text("""
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            WHERE c.relname='document_chunks' AND a.attname='embedding'
        """))
        head = ScriptDirectory(str(Path(__file__).parent / "migrations")).get_current_head()
        assert version and revision == head and dimension == "vector"
        docs = [
            Document(title="STORAGE TEST A", filename="storage-test-a.txt", mime_type="text/plain", embedding_model="storage-fixture"),
            Document(title="STORAGE TEST B", filename="storage-test-b.txt", mime_type="text/plain", embedding_model="storage-fixture"),
        ]
        db.add_all(docs)
        db.flush()
        db.add_all([
            Chunk(document_id=docs[0].id, chunk_index=0, page_number=3, section="VPN", content="Synthetic fixture A", embedding=vector_a),
            Chunk(document_id=docs[1].id, chunk_index=0, page_number=4, section="MFA", content="Synthetic fixture B", embedding=vector_b),
        ])
        db.commit()
        ids = [d.id for d in docs]
    try:
        with Session() as db:
            distance = Chunk.embedding.cosine_distance(vector_a)
            rows = db.execute(select(Chunk, Document, (1 - distance).label("score")).join(Document, Chunk.document_id == Document.id).where(Document.id.in_(ids)).order_by(distance)).all()
            assert len(rows) == 2
            assert rows[0][1].title == "STORAGE TEST A" and rows[0][0].page_number == 3
            assert rows[0][0].section == "VPN" and rows[0][0].content == "Synthetic fixture A"
            assert rows[0][2] > 0.999 and abs(rows[1][2]) < 0.001
            assert len(rows[0][0].embedding) == 384
            print(f"PostgreSQL pgvector {version}; migration {revision}; column {dimension}; persisted rows {len(rows)}; cosine search and metadata PASS")
    finally:
        with Session() as db:
            for doc_id in ids:
                doc = db.get(Document, doc_id)
                if doc:
                    db.delete(doc)
            db.commit()


if __name__ == "__main__":
    main()
