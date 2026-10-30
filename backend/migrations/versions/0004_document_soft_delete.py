"""soft delete for documents

Revision ID: 0004_document_soft_delete
Revises: 0003_responsive_letter_type
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_document_soft_delete"
down_revision: str | None = "0003_responsive_letter_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FTS_TRIGGERS = (
    """
    CREATE TRIGGER documents_fts_after_insert AFTER INSERT ON documents BEGIN
        INSERT INTO document_fts(rowid, title, extracted_text)
        VALUES (new.id, new.title, new.extracted_text);
    END
    """,
    """
    CREATE TRIGGER documents_fts_after_delete AFTER DELETE ON documents BEGIN
        INSERT INTO document_fts(document_fts, rowid, title, extracted_text)
        VALUES ('delete', old.id, old.title, old.extracted_text);
    END
    """,
    """
    CREATE TRIGGER documents_fts_after_update AFTER UPDATE ON documents BEGIN
        INSERT INTO document_fts(document_fts, rowid, title, extracted_text)
        VALUES ('delete', old.id, old.title, old.extracted_text);
        INSERT INTO document_fts(rowid, title, extracted_text)
        VALUES (new.id, new.title, new.extracted_text);
    END
    """,
)


def upgrade() -> None:
    with op.batch_alter_table("documents", recreate="never") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("ALTER TABLE documents ADD COLUMN deleted_by_id INTEGER REFERENCES users (id)")
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
    for trigger in FTS_TRIGGERS:
        op.execute(trigger)
    op.execute("INSERT INTO document_fts(document_fts) VALUES ('rebuild')")
