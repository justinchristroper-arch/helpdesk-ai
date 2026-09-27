"""Persist atomic daily DeepSeek call reservations across API workers."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"


def upgrade():
    op.create_table("generation_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column("identity", sa.String(64), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("day", "scope", "identity"))


def downgrade():
    op.drop_table("generation_usage")
