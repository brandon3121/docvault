"""document_fts sync triggers and document indexes

Revision ID: 0002_documents_search
Revises: 0001_initial
Create Date: 2026-10-29
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002_documents_search"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_INDEXES = {
    "ix_documents_document_date": "document_date",
    "ix_documents_destination_id": "destination_id",
    "ix_documents_document_type_id": "document_type_id",
    "ix_documents_owner_id": "owner_id",
}


def upgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER documents_fts_after_insert AFTER INSERT ON documents BEGIN
            INSERT INTO document_fts(rowid, title, extracted_text)
            VALUES (new.id, new.title, new.extracted_text);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER documents_fts_after_delete AFTER DELETE ON documents BEGIN
            INSERT INTO document_fts(document_fts, rowid, title, extracted_text)
            VALUES ('delete', old.id, old.title, old.extracted_text);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER documents_fts_after_update AFTER UPDATE ON documents BEGIN
            INSERT INTO document_fts(document_fts, rowid, title, extracted_text)
            VALUES ('delete', old.id, old.title, old.extracted_text);
            INSERT INTO document_fts(rowid, title, extracted_text)
            VALUES (new.id, new.title, new.extracted_text);
        END
        """
    )
    op.execute("INSERT INTO document_fts(document_fts) VALUES ('rebuild')")

    for name, column in DOCUMENT_INDEXES.items():
        op.create_index(name, "documents", [column])


def downgrade() -> None:
    for name in DOCUMENT_INDEXES:
        op.drop_index(name, table_name="documents")

    op.execute("DROP TRIGGER IF EXISTS documents_fts_after_update")
    op.execute("DROP TRIGGER IF EXISTS documents_fts_after_delete")
    op.execute("DROP TRIGGER IF EXISTS documents_fts_after_insert")
