"""sha256 unique only among active documents

Revision ID: 0005_active_document_sha256
Revises: 0004_document_soft_delete
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_active_document_sha256"
down_revision: str | None = "0004_document_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNIQUE_NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
ACTIVE_SHA256_INDEX = "uq_documents_sha256_active"

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


def _restore_fts_triggers() -> None:
    for trigger in FTS_TRIGGERS:
        op.execute(trigger)
    op.execute("INSERT INTO document_fts(document_fts) VALUES ('rebuild')")


def upgrade() -> None:
    with op.batch_alter_table("documents", recreate="always", naming_convention=UNIQUE_NAMING) as batch_op:
        batch_op.drop_constraint("uq_documents_sha256", type_="unique")
    _restore_fts_triggers()
    op.create_index(
        ACTIVE_SHA256_INDEX,
        "documents",
        ["sha256"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(ACTIVE_SHA256_INDEX, table_name="documents")
    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.create_unique_constraint("uq_documents_sha256", ["sha256"])
    _restore_fts_triggers()
