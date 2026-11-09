"""Add constraints and analytics indexes for listening events.

Revision ID: 0008_listening_events
Revises: 0007_poi_schema_alignment
"""

from alembic import op


revision = "0008_listening_events"
down_revision = "0007_poi_schema_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOT VALID preserves legacy rows while PostgreSQL enforces each rule for
    # every new or updated row. Legacy cleanup can validate them separately.
    op.execute(
        "ALTER TABLE listening_history ADD CONSTRAINT "
        "ck_listening_history_trigger_type "
        "CHECK (trigger_type IN ('AUTO_LOCATION', 'QR_CODE')) NOT VALID"
    )
    op.execute(
        "ALTER TABLE listening_history ADD CONSTRAINT "
        "ck_listening_history_duration_nonnegative "
        "CHECK (duration_sec IS NULL OR duration_sec >= 0) NOT VALID"
    )
    op.execute(
        "ALTER TABLE listening_history ADD CONSTRAINT "
        "ck_listening_history_completed_after_started "
        "CHECK (completed_at IS NULL OR completed_at >= started_at) NOT VALID"
    )
    op.create_index(
        "ix_listening_history_poi_started_at",
        "listening_history",
        ["poi_id", "started_at"],
    )
    op.create_index(
        "ix_listening_history_installation_started_at",
        "listening_history",
        ["installation_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_listening_history_installation_started_at",
        table_name="listening_history",
    )
    op.drop_index(
        "ix_listening_history_poi_started_at",
        table_name="listening_history",
    )
    op.drop_constraint(
        "ck_listening_history_completed_after_started",
        "listening_history",
        type_="check",
    )
    op.drop_constraint(
        "ck_listening_history_duration_nonnegative",
        "listening_history",
        type_="check",
    )
    op.drop_constraint(
        "ck_listening_history_trigger_type",
        "listening_history",
        type_="check",
    )
