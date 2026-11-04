"""Enforce Language status, normalization, and uniqueness constraints.

Revision ID: 0005_language_constraints
Revises: 0004_identity_constraints
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_language_constraints"
down_revision: str | None = "0004_identity_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Deliberately fail before DDL when existing rows do not already satisfy the
    # approved contract. Migration must not silently rewrite user data.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM language
                WHERE language_status NOT IN ('SUPPORTED', 'UNSUPPORTED')
            ) THEN
                RAISE EXCEPTION 'language contains unsupported status values';
            END IF;
            IF EXISTS (
                SELECT 1 FROM language
                WHERE language_code !~ '^[a-z]{2,3}$'
            ) THEN
                RAISE EXCEPTION 'language contains invalid or unnormalized codes';
            END IF;
            IF EXISTS (
                SELECT 1 FROM language
                WHERE language_name <> btrim(language_name) OR language_name = ''
            ) THEN
                RAISE EXCEPTION 'language contains empty or untrimmed names';
            END IF;
            IF EXISTS (
                SELECT 1 FROM language GROUP BY language_name HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'language contains duplicate names';
            END IF;
        END $$;
        """
    )

    status_enum = postgresql.ENUM(
        "SUPPORTED", "UNSUPPORTED", name="language_status"
    )
    status_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "language",
        "language_status",
        existing_type=sa.String(length=30),
        type_=status_enum,
        postgresql_using="language_status::language_status",
        existing_nullable=False,
    )
    op.create_unique_constraint(
        "language_language_name_key", "language", ["language_name"]
    )
    op.create_check_constraint(
        "ck_language_code_format",
        "language",
        "language_code ~ '^[a-z]{2,3}$'",
    )
    op.create_check_constraint(
        "ck_language_name_nonempty_trimmed",
        "language",
        "language_name = btrim(language_name) AND language_name <> ''",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_language_name_nonempty_trimmed", "language", type_="check"
    )
    op.drop_constraint("ck_language_code_format", "language", type_="check")
    op.drop_constraint(
        "language_language_name_key", "language", type_="unique"
    )
    op.alter_column(
        "language",
        "language_status",
        existing_type=postgresql.ENUM(
            "SUPPORTED", "UNSUPPORTED", name="language_status", create_type=False
        ),
        type_=sa.String(length=30),
        postgresql_using="language_status::text",
        existing_nullable=False,
    )
    postgresql.ENUM(name="language_status").drop(op.get_bind(), checkfirst=True)
