"""Update role, management function, and permission schema.

Revision ID: 0003_update_identity_models
Revises: 0002_align_identifier_types
Create Date: 2026-10-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_update_identity_models"
down_revision = "0002_align_identifier_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "management_function",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column("role", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "role",
        sa.Column("created_by", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "role",
        sa.Column("last_updated_by", sa.String(length=50), nullable=True),
    )
    op.alter_column(
        "role",
        "last_updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.create_foreign_key(
        "role_created_by_fkey",
        "role",
        "manager_user",
        ["created_by"],
        ["id"],
    )
    op.create_foreign_key(
        "role_last_updated_by_fkey",
        "role",
        "manager_user",
        ["last_updated_by"],
        ["id"],
    )
    op.drop_constraint(
        "uq_permission_function_action",
        "permission",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_permission_function_action",
        "permission",
        ["function_id", "action_id"],
    )
    op.drop_constraint(
        "role_last_updated_by_fkey",
        "role",
        type_="foreignkey",
    )
    op.drop_constraint(
        "role_created_by_fkey",
        "role",
        type_="foreignkey",
    )
    op.execute(
        "UPDATE role SET last_updated_at = created_at WHERE last_updated_at IS NULL"
    )
    op.alter_column(
        "role",
        "last_updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_column("role", "last_updated_by")
    op.drop_column("role", "created_by")
    op.drop_column("role", "description")
    op.drop_column("management_function", "description")
