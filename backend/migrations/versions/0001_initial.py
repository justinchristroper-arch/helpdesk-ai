"""Immutable initial DDL; future model edits must use a new migration."""
from pathlib import Path
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    ddl = Path(__file__).with_name("0001_schema.sql").read_text(encoding="utf-8")
    for statement in ddl.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table in ["message_sources", "feedback", "messages", "document_chunks", "conversations", "documents", "users"]:
        op.drop_table(table)
