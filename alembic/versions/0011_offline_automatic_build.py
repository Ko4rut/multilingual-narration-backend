"""Durable offline rebuild requests and immutable manifest release index.

Revision ID: 0011_offline_auto_build
Revises: 0010_manual_trigger
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_offline_auto_build"
down_revision = "0010_manual_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offline_build_request",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("region_id", sa.String(50), nullable=False),
        sa.Column("language_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_offline_build_attempts"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED')",
            name="ck_offline_build_status",
        ),
    )
    op.create_index("ix_offline_build_due", "offline_build_request",
                    ["status", "next_attempt_at"])
    op.create_table(
        "offline_package_release",
        sa.Column("package_id", sa.String(50), sa.ForeignKey(
            "offline_package.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("package_version", sa.Integer(), primary_key=True),
        sa.Column("manifest_url", sa.String(1000), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("package_version >= 1", name="ck_offline_release_version"),
    )


def downgrade() -> None:
    op.drop_table("offline_package_release")
    op.drop_index("ix_offline_build_due", table_name="offline_build_request")
    op.drop_table("offline_build_request")
