"""Add semantic examples and conversation context without rewriting existing data."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0003"
down_revision = "0002"


def upgrade():
    op.add_column("conversations", sa.Column("context", sa.JSON(), nullable=True))
    op.add_column("messages", sa.Column("intent_id", sa.String(100), nullable=True))
    op.add_column("messages", sa.Column("diagnostics", sa.JSON(), nullable=True))
    op.add_column("messages", sa.Column("clarification", sa.JSON(), nullable=True))
    op.create_table("intent_examples",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("intent_id", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("negative", sa.Boolean(), nullable=False),
        sa.Column("embedding_model", sa.String(150), nullable=False),
        sa.Column("dataset_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False))
    op.create_index("ix_intent_examples_intent_id", "intent_examples", ["intent_id"])


def downgrade():
    op.drop_table("intent_examples")
    for column in ("intent_id", "diagnostics", "clarification"):
        op.drop_column("messages", column)
    op.drop_column("conversations", "context")
