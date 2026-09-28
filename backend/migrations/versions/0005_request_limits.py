"""Share request limits across serverless instances; existing data is untouched."""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"


def upgrade():
    op.create_table("request_limits",
        sa.Column("identity", sa.String(64), primary_key=True),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False))
    op.create_index("ix_request_limits_expires_at", "request_limits", ["expires_at"])


def downgrade():
    op.drop_table("request_limits")
