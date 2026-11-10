"""Canonicalize POI and content-audio persistence contracts.

Revision ID: 0009_poi_contract
Revises: 0008_listening_events
"""

from alembic import op


revision = "0009_poi_contract"
down_revision = "0008_listening_events"
branch_labels = None
depends_on = None


_AUDIO_MIME_CHECK = (
    "audio_mime_type IN ('audio/mpeg', 'audio/aac', 'audio/ogg', "
    "'audio/wav', 'audio/mp4', 'audio/webm')"
)


def upgrade() -> None:
    # Khóa các bảng để dữ liệu không thay đổi giữa bước kiểm tra và đổi constraint.
    op.execute(
        "LOCK TABLE point_of_interest, content_audio "
        "IN SHARE ROW EXCLUSIVE MODE"
    )

    # last_updated_by có thể khôi phục chính xác từ người tạo. URL ảnh thì không thể
    # tự suy đoán; migration dừng để người vận hành bổ sung dữ liệu thật trước.
    op.execute(
        "UPDATE point_of_interest SET last_updated_by = created_by "
        "WHERE last_updated_by IS NULL"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM point_of_interest
                WHERE poi_image_url IS NULL OR btrim(poi_image_url) = ''
            ) THEN
                RAISE EXCEPTION
                    'POI migration: poi_image_url is required; backfill real asset URLs first';
            END IF;
            IF EXISTS (
                SELECT 1 FROM point_of_interest
                WHERE upper(poi_status) NOT IN (
                    'ACTIVE', 'INACTIVE', 'MAINTENANCE'
                )
            ) THEN
                RAISE EXCEPTION
                    'POI migration: unsupported poi_status value';
            END IF;
            IF EXISTS (
                SELECT 1 FROM content_audio
                WHERE upper(audio_source_type) NOT IN (
                    'RECORD', 'TTS', 'PRE_GENERATED', 'TTS_GENERATED'
                )
                   OR audio_mime_type NOT IN (
                    'audio/mpeg', 'audio/aac', 'audio/ogg',
                    'audio/wav', 'audio/mp4', 'audio/webm'
                )
            ) THEN
                RAISE EXCEPTION
                    'POI migration: unsupported audio source or MIME type';
            END IF;
        END $$;
        """
    )

    op.execute(
        "UPDATE point_of_interest SET poi_status = CASE "
        "WHEN upper(poi_status) = 'ACTIVE' THEN 'ACTIVE' ELSE 'INACTIVE' END"
    )
    op.execute(
        "UPDATE content_audio SET audio_source_type = CASE "
        "WHEN upper(audio_source_type) IN ('RECORD', 'PRE_GENERATED') THEN 'RECORD' "
        "ELSE 'TTS' END"
    )
    op.execute(
        "UPDATE content_audio SET audio_checksum_sha256 = "
        "lower(audio_checksum_sha256)"
    )

    op.alter_column("point_of_interest", "poi_image_url", nullable=False)
    op.alter_column("point_of_interest", "last_updated_by", nullable=False)
    op.create_check_constraint(
        "ck_point_of_interest_status",
        "point_of_interest",
        "poi_status IN ('ACTIVE', 'INACTIVE')",
    )

    op.drop_constraint(
        "ck_content_audio_source", "content_audio", type_="check"
    )
    op.create_check_constraint(
        "ck_content_audio_source",
        "content_audio",
        "audio_source_type IN ('RECORD', 'TTS')",
    )
    op.create_check_constraint(
        "ck_content_audio_mime", "content_audio", _AUDIO_MIME_CHECK
    )
    op.drop_constraint(
        "content_audio_audio_checksum_sha256_key",
        "content_audio",
        type_="unique",
    )


def downgrade() -> None:
    # Việc khôi phục UNIQUE chỉ an toàn khi không có checksum trùng được tạo sau
    # upgrade. Nếu có, dừng thay vì xóa dữ liệu âm thanh.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM content_audio
                GROUP BY audio_checksum_sha256 HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot restore unique audio checksum while duplicates exist';
            END IF;
        END $$;
        """
    )
    op.create_unique_constraint(
        "content_audio_audio_checksum_sha256_key",
        "content_audio",
        ["audio_checksum_sha256"],
    )
    op.drop_constraint(
        "ck_content_audio_mime", "content_audio", type_="check"
    )
    op.drop_constraint(
        "ck_content_audio_source", "content_audio", type_="check"
    )
    op.create_check_constraint(
        "ck_content_audio_source",
        "content_audio",
        "upper(audio_source_type) IN "
        "('RECORD', 'TTS', 'PRE_GENERATED', 'TTS_GENERATED')",
    )

    op.drop_constraint(
        "ck_point_of_interest_status", "point_of_interest", type_="check"
    )
    op.alter_column("point_of_interest", "last_updated_by", nullable=True)
    op.alter_column("point_of_interest", "poi_image_url", nullable=True)
