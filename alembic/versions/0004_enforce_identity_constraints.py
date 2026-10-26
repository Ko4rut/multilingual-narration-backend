"""Enforce identity status and session invariants.

Revision ID: 0004_enforce_identity_constraints
Revises: 0003_update_identity_models
Create Date: 2026-10-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_enforce_identity_constraints"
down_revision = "0003_update_identity_models"
branch_labels = None
depends_on = None


MANAGER_USER_STATUS = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    name="manager_user_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("UPDATE manager_user SET user_status = upper(btrim(user_status))")
    op.execute(
        "UPDATE manager_user SET user_status = 'INACTIVE' "
        "WHERE user_status = 'DISABLED'"
    )
    MANAGER_USER_STATUS.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "manager_user",
        "user_status",
        existing_type=sa.String(length=30),
        type_=MANAGER_USER_STATUS,
        existing_nullable=False,
        postgresql_using="user_status::manager_user_status",
    )
    op.create_check_constraint(
        "ck_user_session_expires_after_creation",
        "user_session",
        "expires_at > created_at",
    )
    op.create_check_constraint(
        "ck_user_session_revoked_after_creation",
        "user_session",
        "revoked_at IS NULL OR revoked_at >= created_at",
    )
    op.create_index(
        "ix_user_session_expires_at",
        "user_session",
        ["expires_at"],
    )
    op.create_index(
        "ix_role_permission_role_id",
        "role_permission",
        ["role_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_role_permission_role_id", table_name="role_permission")
    op.drop_index("ix_user_session_expires_at", table_name="user_session")
    op.drop_constraint(
        "ck_user_session_revoked_after_creation",
        "user_session",
        type_="check",
    )
    op.drop_constraint(
        "ck_user_session_expires_after_creation",
        "user_session",
        type_="check",
    )
    op.alter_column(
        "manager_user",
        "user_status",
        existing_type=MANAGER_USER_STATUS,
        type_=sa.String(length=30),
        existing_nullable=False,
        postgresql_using="user_status::text",
    )
    MANAGER_USER_STATUS.drop(op.get_bind(), checkfirst=False)
