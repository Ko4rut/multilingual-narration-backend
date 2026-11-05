"""Align Group 3 offline package tables with docs/database-design.md.

Revision ID: 0006_offline_contract
Revises: 0005_language_constraints

Existing package identifiers and item memberships are retained. Legacy package
keys are canonicalized from stored catalog codes; published external manifests
must be rebuilt separately if they still refer to the old key.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_offline_contract"
down_revision = "0005_language_constraints"
branch_labels = None
depends_on = None


PACKAGE_STATUS = postgresql.ENUM(
    "BUILDING", "PUBLISHED", "FAILED",
    name="offline_package_status",
    create_type=False,
)


def upgrade() -> None:
    # Prevent writes between the collision preflight and the unique constraint.
    op.execute("LOCK TABLE offline_package, offline_package_item IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM offline_package
                GROUP BY region_id, language_id, category_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'offline_package has duplicate filter combinations; reconcile package versions before upgrade';
            END IF;
            IF EXISTS (
                SELECT 1 FROM offline_package_item
                GROUP BY package_id, poi_content_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'offline_package_item has duplicate package/content memberships; reconcile before upgrade';
            END IF;
            IF EXISTS (
                SELECT 1 FROM offline_package
                WHERE package_version < 1 OR schema_version < 1
                   OR total_size < 0
                   OR (published_at IS NOT NULL AND published_at < created_at)
            ) THEN
                RAISE EXCEPTION 'offline_package contains invalid version, size, or publication timestamps';
            END IF;
            IF EXISTS (
                SELECT 1 FROM offline_package_item WHERE content_version < 1
            ) THEN
                RAISE EXCEPTION 'offline_package_item contains invalid content_version';
            END IF;
            IF EXISTS (
                SELECT 1 FROM offline_package
                WHERE upper(btrim(package_status)) NOT IN ('BUILDING', 'PUBLISHED', 'FAILED')
            ) THEN
                RAISE EXCEPTION 'offline_package contains unknown package_status values';
            END IF;
        END $$;
        """
    )

    # Canonical package_key is derived from the filter, not from an old display
    # slug. No POI/content/audio rows or physical assets are deleted.
    op.execute(
        """
        UPDATE offline_package AS p
        SET package_key =
            CASE
                WHEN p.category_id IS NULL THEN ''
                ELSE 'cat:' || (
                    SELECT c.category_code FROM poi_category AS c
                    WHERE c.id = p.category_id
                ) || '|'
            END
            || 'region:' || (
                SELECT r.region_code FROM region AS r WHERE r.id = p.region_id
            )
            || '|lang:' || (
                SELECT l.language_code FROM language AS l WHERE l.id = p.language_id
            )
        """
    )
    op.execute("UPDATE offline_package SET package_status = upper(btrim(package_status))")

    op.drop_constraint(
        "uq_offline_package_key_version", "offline_package", type_="unique"
    )
    op.create_unique_constraint(
        "uq_offline_package_key", "offline_package", ["package_key"]
    )
    op.drop_constraint(
        "offline_package_package_checksum_sha256_key",
        "offline_package",
        type_="unique",
    )
    op.alter_column(
        "offline_package", "package_url",
        existing_type=sa.String(length=1000), existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "offline_package", "total_size",
        existing_type=sa.Integer(), type_=sa.BigInteger(),
        existing_nullable=False, nullable=True,
    )
    op.alter_column(
        "offline_package", "package_checksum_sha256",
        existing_type=sa.String(length=64), existing_nullable=False,
        nullable=True,
    )
    PACKAGE_STATUS.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "offline_package", "package_status",
        existing_type=sa.String(length=30), type_=PACKAGE_STATUS,
        existing_nullable=False,
        postgresql_using="package_status::offline_package_status",
    )

    op.create_check_constraint(
        "ck_offline_package_version_positive",
        "offline_package", "package_version >= 1",
    )
    op.create_check_constraint(
        "ck_offline_package_schema_version_positive",
        "offline_package", "schema_version >= 1",
    )
    op.create_check_constraint(
        "ck_offline_package_total_size_nonnegative",
        "offline_package", "total_size IS NULL OR total_size >= 0",
    )
    op.create_check_constraint(
        "ck_offline_package_published_after_creation",
        "offline_package",
        "published_at IS NULL OR published_at >= created_at",
    )
    op.create_index(
        "ix_offline_package_region_language", "offline_package",
        ["region_id", "language_id"],
    )

    op.drop_constraint(
        "uq_offline_package_item_payload",
        "offline_package_item",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_offline_package_item_package_content",
        "offline_package_item",
        ["package_id", "poi_content_id"],
    )
    op.create_check_constraint(
        "ck_offline_package_item_content_version_positive",
        "offline_package_item", "content_version >= 1",
    )


def downgrade() -> None:
    # The legacy schema cannot represent nullable manifest fields or large sizes.
    # Refuse to discard data merely to allow a rollback.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM offline_package
                WHERE package_url IS NULL OR total_size IS NULL
                   OR package_checksum_sha256 IS NULL
                   OR total_size > 2147483647
            ) THEN
                RAISE EXCEPTION 'offline_package has values incompatible with legacy NOT NULL/INTEGER columns';
            END IF;
            IF EXISTS (
                SELECT 1 FROM offline_package
                GROUP BY package_checksum_sha256 HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION 'offline_package has duplicate checksums incompatible with legacy UNIQUE';
            END IF;
        END $$;
        """
    )

    op.drop_constraint(
        "ck_offline_package_item_content_version_positive",
        "offline_package_item", type_="check",
    )
    op.drop_constraint(
        "uq_offline_package_item_package_content",
        "offline_package_item", type_="unique",
    )
    op.create_unique_constraint(
        "uq_offline_package_item_payload",
        "offline_package_item",
        ["package_id", "poi_id", "poi_content_id", "audio_id"],
    )

    op.drop_index(
        "ix_offline_package_region_language", table_name="offline_package"
    )
    for name in (
        "ck_offline_package_published_after_creation",
        "ck_offline_package_total_size_nonnegative",
        "ck_offline_package_schema_version_positive",
        "ck_offline_package_version_positive",
    ):
        op.drop_constraint(name, "offline_package", type_="check")

    op.alter_column(
        "offline_package", "package_status",
        existing_type=PACKAGE_STATUS, type_=sa.String(length=30),
        existing_nullable=False, postgresql_using="package_status::text",
    )
    PACKAGE_STATUS.drop(op.get_bind(), checkfirst=False)

    op.alter_column(
        "offline_package", "package_checksum_sha256",
        existing_type=sa.String(length=64), existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "offline_package", "total_size",
        existing_type=sa.BigInteger(), type_=sa.Integer(),
        existing_nullable=True, nullable=False,
    )
    op.alter_column(
        "offline_package", "package_url",
        existing_type=sa.String(length=1000), existing_nullable=True,
        nullable=False,
    )
    op.create_unique_constraint(
        "offline_package_package_checksum_sha256_key",
        "offline_package", ["package_checksum_sha256"],
    )
    op.drop_constraint(
        "uq_offline_package_key", "offline_package", type_="unique"
    )
    op.create_unique_constraint(
        "uq_offline_package_key_version",
        "offline_package", ["package_key", "package_version"],
    )
