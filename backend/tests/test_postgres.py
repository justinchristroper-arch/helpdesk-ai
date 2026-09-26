"""Opt-in tests use an isolated schema inside TEST_DATABASE_URL, never drop public."""
import os
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models import Base, Chunk, Document


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires PostgreSQL with pgvector: set TEST_DATABASE_URL")
def test_vector_persistence_and_cosine_retrieval():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    schema = "test_" + uuid.uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(connection)
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                doc = Document(title="VPN", filename="vpn.md", mime_type="text/markdown", embedding_model="test")
                db.add(doc)
                db.flush()
                vector = [1.0] + [0.0] * 1535
                db.add(Chunk(document_id=doc.id, chunk_index=0, content="VPN requires approval", embedding=vector))
                db.commit()
                db.expire_all()
                result = db.execute(select(Chunk, (1 - Chunk.embedding.cosine_distance(vector)).label("score"))).one()
                assert result[0].content == "VPN requires approval"
                assert result[1] == pytest.approx(1.0)
        finally:
            transaction.rollback()
    engine.dispose()
