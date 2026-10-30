"""seed the fixed document type

Revision ID: 0003_responsive_letter_type
Revises: 0002_documents_search
Create Date: 2026-10-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_responsive_letter_type"
down_revision: str | None = "0002_documents_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RESPONSIVE_LETTER = "Carta responsiva"


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "INSERT INTO document_types (name) SELECT :name "
            "WHERE NOT EXISTS (SELECT 1 FROM document_types WHERE name = :name)"
        ),
        {"name": RESPONSIVE_LETTER},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "DELETE FROM document_types WHERE name = :name AND NOT EXISTS ("
            "SELECT 1 FROM documents WHERE documents.document_type_id = document_types.id)"
        ),
        {"name": RESPONSIVE_LETTER},
    )
