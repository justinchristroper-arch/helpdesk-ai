"""Permit the configured local 384-dimension model and existing 1536-dimension data.

Queries always filter by document embedding_model, so dimensions are not mixed.
"""
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector")


def downgrade():
    raise RuntimeError("Downgrade needs a deliberate reindex because vectors may have different dimensions.")
