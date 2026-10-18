"""Create the complete schema represented by the project ERD.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "management_function",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "region",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("region_name", sa.String(150), nullable=False),
        sa.Column("region_code", sa.String(30), nullable=False, unique=True),
    )
    op.create_table(
        "language",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("language_code", sa.String(10), nullable=False, unique=True),
        sa.Column("language_name", sa.String(100), nullable=False),
        sa.Column("language_status", sa.String(30), nullable=False),
    )
    op.create_index("ix_language_language_status", "language", ["language_status"])
    op.create_table(
        "poi_category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_name", sa.String(120), nullable=False),
        sa.Column("category_code", sa.String(30), nullable=False, unique=True),
    )
    op.create_table(
        "permission",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "function_id",
            sa.Integer(),
            sa.ForeignKey("management_function.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "action_id",
            sa.Integer(),
            sa.ForeignKey("action.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "function_id",
            "action_id",
            name="uq_permission_function_action",
        ),
    )
    op.create_index("ix_permission_function_id", "permission", ["function_id"])
    op.create_index("ix_permission_action_id", "permission", ["action_id"])
    op.create_table(
        "role_permission",
        sa.Column(
            "permission_id",
            sa.Integer(),
            sa.ForeignKey("permission.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("role.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "manager_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("role.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("user_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_manager_user_role_id", "manager_user", ["role_id"])
    op.create_index("ix_manager_user_user_status", "manager_user", ["user_status"])
    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "refresh_token_hash",
            sa.String(64),
            nullable=False,
            unique=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])
    op.create_table(
        "point_of_interest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("region.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("poi_image_url", sa.String(1000), nullable=True),
        sa.Column("image_checksum_sha256", sa.String(64), nullable=True),
        sa.Column("poi_qr_code", sa.String(255), nullable=False, unique=True),
        sa.Column("poi_name", sa.String(255), nullable=False),
        sa.Column("poi_location", sa.String(500), nullable=False),
        sa.Column("poi_status", sa.String(30), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("trigger_radius_meter", sa.Numeric(8, 2), nullable=False),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "last_updated_by",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_point_of_interest_region_id", "point_of_interest", ["region_id"]
    )
    op.create_index(
        "ix_point_of_interest_poi_status", "point_of_interest", ["poi_status"]
    )
    op.create_index(
        "ix_point_of_interest_created_by", "point_of_interest", ["created_by"]
    )
    op.create_index(
        "ix_point_of_interest_last_updated_by",
        "point_of_interest",
        ["last_updated_by"],
    )
    op.create_table(
        "poi_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poi_id",
            sa.Integer(),
            sa.ForeignKey("point_of_interest.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "language_id",
            sa.Integer(),
            sa.ForeignKey("language.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("narration_title", sa.String(255), nullable=False),
        sa.Column("narration_script", sa.Text(), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("content_status", sa.String(30), nullable=False),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "published_by",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "poi_id",
            "language_id",
            "content_version",
            name="uq_poi_content_poi_language_version",
        ),
    )
    op.create_index("ix_poi_content_poi_id", "poi_content", ["poi_id"])
    op.create_index("ix_poi_content_language_id", "poi_content", ["language_id"])
    op.create_index(
        "ix_poi_content_content_status", "poi_content", ["content_status"]
    )
    op.create_index("ix_poi_content_created_by", "poi_content", ["created_by"])
    op.create_index("ix_poi_content_approved_by", "poi_content", ["approved_by"])
    op.create_index("ix_poi_content_published_by", "poi_content", ["published_by"])
    op.create_table(
        "content_audio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poi_content_id",
            sa.Integer(),
            sa.ForeignKey("poi_content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("audio_url", sa.String(1000), nullable=False),
        sa.Column("audio_size", sa.Integer(), nullable=False),
        sa.Column("audio_source_type", sa.String(30), nullable=False),
        sa.Column("audio_duration_sec", sa.Integer(), nullable=False),
        sa.Column("audio_mime_type", sa.String(100), nullable=False),
        sa.Column(
            "audio_checksum_sha256",
            sa.String(64),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_content_audio_poi_content_id", "content_audio", ["poi_content_id"]
    )
    op.create_table(
        "listening_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("installation_id", sa.String(100), nullable=False),
        sa.Column(
            "poi_content_id",
            sa.Integer(),
            sa.ForeignKey("poi_content.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "poi_id",
            sa.Integer(),
            sa.ForeignKey("point_of_interest.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_listening_history_installation_id",
        "listening_history",
        ["installation_id"],
    )
    op.create_index(
        "ix_listening_history_poi_content_id",
        "listening_history",
        ["poi_content_id"],
    )
    op.create_index(
        "ix_listening_history_poi_id", "listening_history", ["poi_id"]
    )
    op.create_index(
        "ix_listening_history_trigger_type",
        "listening_history",
        ["trigger_type"],
    )
    op.create_table(
        "poi_category_mapping",
        sa.Column(
            "poi_id",
            sa.Integer(),
            sa.ForeignKey("point_of_interest.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "poi_category_id",
            sa.Integer(),
            sa.ForeignKey("poi_category.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "offline_package",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("poi_category.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("region.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "language_id",
            sa.Integer(),
            sa.ForeignKey("language.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("package_key", sa.String(100), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("package_url", sa.String(1000), nullable=False),
        sa.Column("package_version", sa.Integer(), nullable=False),
        sa.Column("total_size", sa.Integer(), nullable=False),
        sa.Column(
            "package_checksum_sha256",
            sa.String(64),
            nullable=False,
            unique=True,
        ),
        sa.Column("package_status", sa.String(30), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "package_key",
            "package_version",
            name="uq_offline_package_key_version",
        ),
    )
    op.create_index(
        "ix_offline_package_category_id", "offline_package", ["category_id"]
    )
    op.create_index(
        "ix_offline_package_region_id", "offline_package", ["region_id"]
    )
    op.create_index(
        "ix_offline_package_language_id", "offline_package", ["language_id"]
    )
    op.create_index(
        "ix_offline_package_package_status", "offline_package", ["package_status"]
    )
    op.create_table(
        "offline_package_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "package_id",
            sa.Integer(),
            sa.ForeignKey("offline_package.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "poi_id",
            sa.Integer(),
            sa.ForeignKey("point_of_interest.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "poi_content_id",
            sa.Integer(),
            sa.ForeignKey("poi_content.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "audio_id",
            sa.Integer(),
            sa.ForeignKey("content_audio.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "package_id",
            "poi_id",
            "poi_content_id",
            "audio_id",
            name="uq_offline_package_item_payload",
        ),
    )
    op.create_index(
        "ix_offline_package_item_package_id",
        "offline_package_item",
        ["package_id"],
    )
    op.create_index(
        "ix_offline_package_item_poi_id", "offline_package_item", ["poi_id"]
    )
    op.create_index(
        "ix_offline_package_item_poi_content_id",
        "offline_package_item",
        ["poi_content_id"],
    )
    op.create_index(
        "ix_offline_package_item_audio_id", "offline_package_item", ["audio_id"]
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("manager_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("offline_package_item")
    op.drop_table("offline_package")
    op.drop_table("poi_category_mapping")
    op.drop_table("listening_history")
    op.drop_table("content_audio")
    op.drop_table("poi_content")
    op.drop_table("point_of_interest")
    op.drop_table("user_session")
    op.drop_table("manager_user")
    op.drop_table("role_permission")
    op.drop_table("permission")
    op.drop_table("poi_category")
    op.drop_table("language")
    op.drop_table("region")
    op.drop_table("role")
    op.drop_table("management_function")
    op.drop_table("action")
