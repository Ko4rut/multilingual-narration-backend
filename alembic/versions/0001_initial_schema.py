"""create complete ERD schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("action", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True))
    op.create_table("management_function", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True))
    op.create_table("role", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True))
    op.create_table("region", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(150), nullable=False, unique=True))
    op.create_table("language", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("language_code", sa.String(10), nullable=False, unique=True), sa.Column("language_name", sa.String(100), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("poi_category", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True))
    op.create_table("permission", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("function_id", sa.Integer(), sa.ForeignKey("management_function.id", ondelete="RESTRICT"), nullable=False), sa.Column("action_id", sa.Integer(), sa.ForeignKey("action.id", ondelete="RESTRICT"), nullable=False), sa.UniqueConstraint("function_id", "action_id", name="uq_permission_function_action"))
    op.create_index("ix_permission_function_id", "permission", ["function_id"])
    op.create_index("ix_permission_action_id", "permission", ["action_id"])
    op.create_table("role_permission", sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True), sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("management_user", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email_address", sa.String(255), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("refresh_token", sa.String(512)), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="RESTRICT"), nullable=False), sa.Column("full_name", sa.String(200), nullable=False), sa.Column("gender", sa.String(30)), sa.Column("date_of_birth", sa.Date()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_delete", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_management_user_role_id", "management_user", ["role_id"])
    op.create_table("point_of_interest", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("region_id", sa.Integer(), sa.ForeignKey("region.id", ondelete="RESTRICT"), nullable=False), sa.Column("image_url", sa.String(1000)), sa.Column("qr_code", sa.String(255), nullable=False, unique=True), sa.Column("poi_priority", sa.Integer(), nullable=False), sa.Column("poi_name", sa.String(255), nullable=False), sa.Column("latitude", sa.Numeric(9, 6), nullable=False), sa.Column("longitude", sa.Numeric(9, 6), nullable=False), sa.Column("trigger_radius", sa.Numeric(8, 2), nullable=False), sa.Column("poi_location", sa.String(500), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_point_of_interest_region_id", "point_of_interest", ["region_id"])
    op.create_index("ix_point_of_interest_created_by", "point_of_interest", ["created_by"])
    op.create_index("ix_point_of_interest_qr_code", "point_of_interest", ["qr_code"])
    op.create_table("poi_content", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("poi_id", sa.Integer(), sa.ForeignKey("point_of_interest.id", ondelete="CASCADE"), nullable=False), sa.Column("language_id", sa.Integer(), sa.ForeignKey("language.id", ondelete="RESTRICT"), nullable=False), sa.Column("narration_title", sa.String(255), nullable=False), sa.Column("narration_script", sa.Text(), nullable=False), sa.Column("content_status", sa.String(30), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("poi_id", "language_id", name="uq_poi_content_poi_language"))
    op.create_index("ix_poi_content_poi_id", "poi_content", ["poi_id"])
    op.create_index("ix_poi_content_language_id", "poi_content", ["language_id"])
    op.create_index("ix_poi_content_created_by", "poi_content", ["created_by"])
    op.create_table("content_audio", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("poi_content_id", sa.Integer(), sa.ForeignKey("poi_content.id", ondelete="CASCADE"), nullable=False), sa.Column("audio_url", sa.String(1000), nullable=False), sa.Column("audio_size", sa.Integer(), nullable=False), sa.Column("audio_source_type", sa.String(30), nullable=False), sa.Column("checksum_sha25", sa.String(64), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_content_audio_poi_content_id", "content_audio", ["poi_content_id"])
    op.create_table("listening_history", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("poi_id", sa.Integer(), sa.ForeignKey("point_of_interest.id", ondelete="RESTRICT"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("duration_sec", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_listening_history_poi_id", "listening_history", ["poi_id"])
    op.create_table("poi_category_mapping", sa.Column("poi_id", sa.Integer(), sa.ForeignKey("point_of_interest.id", ondelete="CASCADE"), primary_key=True), sa.Column("poi_category_id", sa.Integer(), sa.ForeignKey("poi_category.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("offline_package", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("category_id", sa.Integer(), sa.ForeignKey("poi_category.id", ondelete="RESTRICT")), sa.Column("region_id", sa.Integer(), sa.ForeignKey("region.id", ondelete="RESTRICT"), nullable=False), sa.Column("language_id", sa.Integer(), sa.ForeignKey("language.id", ondelete="RESTRICT"), nullable=False), sa.Column("name", sa.String(255), nullable=False, unique=True), sa.Column("total_size", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_offline_package_category_id", "offline_package", ["category_id"])
    op.create_index("ix_offline_package_region_id", "offline_package", ["region_id"])
    op.create_index("ix_offline_package_language_id", "offline_package", ["language_id"])
    op.create_table("audit_log", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False), sa.Column("action", sa.String(100), nullable=False), sa.Column("entity_type", sa.String(100), nullable=False), sa.Column("entity_id", sa.Integer(), nullable=False), sa.Column("old_values", postgresql.JSONB()), sa.Column("new_values", postgresql.JSONB()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])


def downgrade():
    op.drop_table("audit_log")
    op.drop_table("offline_package")
    op.drop_table("poi_category_mapping")
    op.drop_table("listening_history")
    op.drop_table("content_audio")
    op.drop_table("poi_content")
    op.drop_table("point_of_interest")
    op.drop_table("management_user")
    op.drop_table("role_permission")
    op.drop_table("permission")
    op.drop_table("poi_category")
    op.drop_table("language")
    op.drop_table("region")
    op.drop_table("role")
    op.drop_table("management_function")
    op.drop_table("action")
