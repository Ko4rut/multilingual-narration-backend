"""Allow manually triggered listening events.

Revision ID: 0010_manual_trigger
Revises: 0009_poi_contract
"""

from alembic import op


revision = "0010_manual_trigger"
down_revision = "0009_poi_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_listening_history_trigger_type",
        "listening_history",
        type_="check",
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM listening_history
                WHERE upper(trigger_type) NOT IN (
                    'AUTO_LOCATION', 'QR_CODE', 'MANUAL', 'GPS'
                )
            ) THEN
                RAISE EXCEPTION
                    'Listening migration: unsupported trigger_type value';
            END IF;
        END $$;
        """
    )
    op.execute(
        "UPDATE listening_history SET trigger_type = CASE "
        "WHEN upper(trigger_type) = 'GPS' THEN 'AUTO_LOCATION' "
        "ELSE upper(trigger_type) END"
    )
    op.create_check_constraint(
        "ck_listening_history_trigger_type",
        "listening_history",
        "trigger_type IN ('AUTO_LOCATION', 'QR_CODE', 'MANUAL')",
    )


def downgrade() -> None:
    # Không âm thầm xóa hoặc đổi ý nghĩa các sự kiện MANUAL đã ghi nhận.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM listening_history WHERE trigger_type = 'MANUAL'
            ) THEN
                RAISE EXCEPTION
                    'Cannot remove MANUAL trigger while listening events use it';
            END IF;
        END $$;
        """
    )
    op.drop_constraint(
        "ck_listening_history_trigger_type",
        "listening_history",
        type_="check",
    )
    op.create_check_constraint(
        "ck_listening_history_trigger_type",
        "listening_history",
        "trigger_type IN ('AUTO_LOCATION', 'QR_CODE')",
    )
