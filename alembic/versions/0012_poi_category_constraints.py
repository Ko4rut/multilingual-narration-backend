"""Protect POI Category master data and prevent cascading category deletion.

Revision ID: 0012_poi_category_constraints
Revises: 0011_offline_auto_build
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0012_poi_category_constraints"
down_revision: str | None = "0011_offline_auto_build"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Fail fast on legacy bad rows. This migration never silently renames codes,
    # since category_code can be embedded in immutable offline manifest keys.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM poi_category
                WHERE category_name <> btrim(category_name) OR category_name = ''
            ) THEN
                RAISE EXCEPTION 'poi_category has empty/untrimmed names';
            END IF;
            IF EXISTS (
                SELECT 1 FROM poi_category
                WHERE category_code !~ '^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$'
            ) THEN
                RAISE EXCEPTION 'poi_category contains invalid legacy codes';
            END IF;
            IF EXISTS (
                SELECT 1 FROM poi_category
                GROUP BY category_name HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION 'poi_category contains duplicate category names';
            END IF;
        END $$;
        """
    )
    op.create_unique_constraint(
        "uq_poi_category_name", "poi_category", ["category_name"]
    )
    op.create_check_constraint(
        "ck_poi_category_name_nonempty_trimmed",
        "poi_category",
        "category_name = btrim(category_name) AND category_name <> ''",
    )
    op.create_check_constraint(
        "ck_poi_category_code_format",
        "poi_category",
        "category_code ~ '^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$'",
    )

    # Previously CASCADE: a delete could silently remove category assignments.
    # RESTRICT guarantees the same safety for manual SQL and concurrent writes.
    op.drop_constraint(
        "poi_category_mapping_poi_category_id_fkey",
        "poi_category_mapping", type_="foreignkey",
    )
    op.create_foreign_key(
        "poi_category_mapping_poi_category_id_fkey",
        "poi_category_mapping", "poi_category",
        ["poi_category_id"], ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "poi_category_mapping_poi_category_id_fkey",
        "poi_category_mapping", type_="foreignkey",
    )
    op.create_foreign_key(
        "poi_category_mapping_poi_category_id_fkey",
        "poi_category_mapping", "poi_category",
        ["poi_category_id"], ["id"], ondelete="CASCADE",
    )
    op.drop_constraint("ck_poi_category_code_format", "poi_category", type_="check")
    op.drop_constraint(
        "ck_poi_category_name_nonempty_trimmed", "poi_category", type_="check",
    )
    op.drop_constraint("uq_poi_category_name", "poi_category", type_="unique")
