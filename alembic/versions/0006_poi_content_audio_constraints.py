"""Enforce narration versions, one published version and one audio per content.

Revision ID: 0006_poi_content_audio
Revises: 0005_poi_management
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_poi_content_audio"
down_revision = "0005_poi_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing conflicts abort the revision; do not silently discard versions/audio.
    op.create_check_constraint("ck_poi_content_version", "poi_content", "content_version >= 1")
    op.create_check_constraint(
        "ck_poi_content_status", "poi_content",
        "upper(content_status) IN ('DRAFT', 'WAITING_APPROVAL', 'REJECTED', 'APPROVED', 'PUBLISHED', 'ARCHIVED')",
    )
    op.create_check_constraint("ck_poi_content_approved_at", "poi_content", "approved_at IS NULL OR approved_at >= created_at")
    op.create_check_constraint(
        "ck_poi_content_published_at", "poi_content",
        "published_at IS NULL OR approved_at IS NULL OR published_at >= approved_at",
    )
    op.create_index("ix_poi_content_distribution", "poi_content", ["poi_id", "language_id", "content_status"])
    op.create_index(
        "uq_poi_content_published_language", "poi_content", ["poi_id", "language_id"],
        unique=True, postgresql_where=sa.text("upper(content_status) = 'PUBLISHED'"),
    )
    op.create_unique_constraint("uq_content_audio_content", "content_audio", ["poi_content_id"])
    op.alter_column("content_audio", "audio_size", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
    op.create_check_constraint("ck_content_audio_size", "content_audio", "audio_size >= 0")
    op.create_check_constraint("ck_content_audio_duration", "content_audio", "audio_duration_sec >= 0")
    op.create_check_constraint(
        "ck_content_audio_source", "content_audio",
        "upper(audio_source_type) IN ('RECORD', 'TTS', 'PRE_GENERATED', 'TTS_GENERATED')",
    )
    op.create_index("ix_content_audio_audio_source_type", "content_audio", ["audio_source_type"])


def downgrade() -> None:
    op.drop_index("ix_content_audio_audio_source_type", table_name="content_audio")
    for name in ("ck_content_audio_source", "ck_content_audio_duration", "ck_content_audio_size"):
        op.drop_constraint(name, "content_audio", type_="check")
    # PostgreSQL refuses out-of-range values rather than truncating large sizes.
    op.alter_column("content_audio", "audio_size", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    op.drop_constraint("uq_content_audio_content", "content_audio", type_="unique")
    op.drop_index("uq_poi_content_published_language", table_name="poi_content")
    op.drop_index("ix_poi_content_distribution", table_name="poi_content")
    for name in ("ck_poi_content_published_at", "ck_poi_content_approved_at", "ck_poi_content_status", "ck_poi_content_version"):
        op.drop_constraint(name, "poi_content", type_="check")
