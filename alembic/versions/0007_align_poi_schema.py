"""Align merged POI, Content and Audio models with PostgreSQL schema.

Revision ID: 0007_poi_schema_alignment
Revises: 0006_offline_contract

The POI feature merged its models without the corresponding two migrations.
Apply all missing constraints and indexes in one new revision (do not rewrite
previously applied migrations). Validate existing rows before any DDL; never
silently drop content, audio or POIs.
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_poi_schema_alignment"
down_revision = "0006_offline_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Block concurrent writes between validation and UNIQUE/index creation.
    # PostgreSQL transactional DDL rolls back all changes if anything fails.
    op.execute(
        "LOCK TABLE point_of_interest, poi_content, content_audio "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM point_of_interest
                GROUP BY poi_location HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'POI migration: duplicate poi_location values; reconcile first';
            END IF;
            IF EXISTS (
                SELECT 1 FROM point_of_interest
                WHERE latitude NOT BETWEEN -90 AND 90
                   OR longitude NOT BETWEEN -180 AND 180
                   OR trigger_radius_meter <= 0
            ) THEN
                RAISE EXCEPTION
                    'POI migration: invalid latitude, longitude or trigger radius';
            END IF;
            IF EXISTS (
                SELECT 1 FROM poi_content
                WHERE content_version < 1
                   OR upper(content_status) NOT IN (
                       'DRAFT', 'WAITING_APPROVAL', 'REJECTED',
                       'APPROVED', 'PUBLISHED', 'ARCHIVED'
                   )
                   OR (approved_at IS NOT NULL AND approved_at < created_at)
                   OR (published_at IS NOT NULL AND approved_at IS NOT NULL
                       AND published_at < approved_at)
            ) THEN
                RAISE EXCEPTION
                    'POI migration: invalid content version, status or timestamps';
            END IF;
            IF EXISTS (
                SELECT 1 FROM poi_content
                WHERE upper(content_status) = 'PUBLISHED'
                GROUP BY poi_id, language_id HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'POI migration: multiple PUBLISHED content rows per POI/language';
            END IF;
            IF EXISTS (
                SELECT 1 FROM content_audio
                GROUP BY poi_content_id HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'POI migration: multiple audio rows per content';
            END IF;
            IF EXISTS (
                SELECT 1 FROM content_audio
                WHERE audio_size < 0 OR audio_duration_sec < 0
                   OR upper(audio_source_type) NOT IN (
                       'RECORD', 'TTS', 'PRE_GENERATED', 'TTS_GENERATED'
                   )
            ) THEN
                RAISE EXCEPTION
                    'POI migration: invalid audio size, duration or source';
            END IF;
        END $$;
        """
    )

    # Existing audio_size is INTEGER in 0001; the merged ORM uses BIGINT.
    op.alter_column(
        "content_audio", "audio_size",
        existing_type=sa.Integer(), type_=sa.BigInteger(),
        existing_nullable=False,
    )

    op.create_unique_constraint(
        "uq_point_of_interest_location", "point_of_interest",
        ["poi_location"],
    )
    op.create_check_constraint(
        "ck_poi_latitude", "point_of_interest",
        "latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        "ck_poi_longitude", "point_of_interest",
        "longitude BETWEEN -180 AND 180",
    )
    op.create_check_constraint(
        "ck_poi_radius", "point_of_interest",
        "trigger_radius_meter > 0",
    )
    op.create_index(
        "ix_point_of_interest_coordinates", "point_of_interest",
        ["latitude", "longitude"],
    )
    op.create_index(
        "ix_poi_category_mapping_poi_category_id", "poi_category_mapping",
        ["poi_category_id"],
    )

    op.create_check_constraint(
        "ck_poi_content_version", "poi_content", "content_version >= 1"
    )
    op.create_check_constraint(
        "ck_poi_content_status", "poi_content",
        "upper(content_status) IN "
        "('DRAFT', 'WAITING_APPROVAL', 'REJECTED', 'APPROVED', "
        "'PUBLISHED', 'ARCHIVED')",
    )
    op.create_check_constraint(
        "ck_poi_content_approved_at", "poi_content",
        "approved_at IS NULL OR approved_at >= created_at",
    )
    op.create_check_constraint(
        "ck_poi_content_published_at", "poi_content",
        "published_at IS NULL OR approved_at IS NULL "
        "OR published_at >= approved_at",
    )
    op.create_index(
        "ix_poi_content_distribution", "poi_content",
        ["poi_id", "language_id", "content_status"],
    )
    op.create_index(
        "uq_poi_content_published_language", "poi_content",
        ["poi_id", "language_id"],
        unique=True,
        postgresql_where=sa.text("upper(content_status) = 'PUBLISHED'"),
    )

    op.create_unique_constraint(
        "uq_content_audio_content", "content_audio",
        ["poi_content_id"],
    )
    op.create_check_constraint(
        "ck_content_audio_size", "content_audio", "audio_size >= 0"
    )
    op.create_check_constraint(
        "ck_content_audio_duration", "content_audio",
        "audio_duration_sec >= 0",
    )
    op.create_check_constraint(
        "ck_content_audio_source", "content_audio",
        "upper(audio_source_type) IN "
        "('RECORD', 'TTS', 'PRE_GENERATED', 'TTS_GENERATED')",
    )
    op.create_index(
        "ix_content_audio_audio_source_type", "content_audio",
        ["audio_source_type"],
    )


def downgrade() -> None:
    # No truncation: old INTEGER column cannot hold larger audio files.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM content_audio
                WHERE audio_size > 2147483647 OR audio_size < -2147483648
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade audio_size BIGINT to INTEGER without data loss';
            END IF;
        END $$;
        """
    )

    op.drop_index(
        "ix_content_audio_audio_source_type", table_name="content_audio"
    )
    for name in (
        "ck_content_audio_source",
        "ck_content_audio_duration",
        "ck_content_audio_size",
    ):
        op.drop_constraint(name, "content_audio", type_="check")
    op.drop_constraint(
        "uq_content_audio_content", "content_audio", type_="unique"
    )

    op.drop_index(
        "uq_poi_content_published_language", table_name="poi_content"
    )
    op.drop_index(
        "ix_poi_content_distribution", table_name="poi_content"
    )
    for name in (
        "ck_poi_content_published_at",
        "ck_poi_content_approved_at",
        "ck_poi_content_status",
        "ck_poi_content_version",
    ):
        op.drop_constraint(name, "poi_content", type_="check")

    op.drop_index(
        "ix_poi_category_mapping_poi_category_id",
        table_name="poi_category_mapping",
    )
    op.drop_index(
        "ix_point_of_interest_coordinates", table_name="point_of_interest"
    )
    for name in ("ck_poi_radius", "ck_poi_longitude", "ck_poi_latitude"):
        op.drop_constraint(name, "point_of_interest", type_="check")
    op.drop_constraint(
        "uq_point_of_interest_location", "point_of_interest", type_="unique"
    )

    op.alter_column(
        "content_audio", "audio_size",
        existing_type=sa.BigInteger(), type_=sa.Integer(),
        existing_nullable=False,
    )
