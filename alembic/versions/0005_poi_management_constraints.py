"""Enforce POI management constraints and lookup indexes.

Revision ID: 0005_poi_management
Revises: 0004_identity_constraints
"""

from alembic import op


revision = "0005_poi_management"
down_revision = "0004_identity_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail atomically on conflicting existing data; never rewrite/delete it.
    op.create_unique_constraint("uq_point_of_interest_location", "point_of_interest", ["poi_location"])
    op.create_check_constraint("ck_poi_latitude", "point_of_interest", "latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_poi_longitude", "point_of_interest", "longitude BETWEEN -180 AND 180")
    op.create_check_constraint("ck_poi_radius", "point_of_interest", "trigger_radius_meter > 0")
    op.create_index("ix_point_of_interest_coordinates", "point_of_interest", ["latitude", "longitude"])
    op.create_index("ix_poi_category_mapping_poi_category_id", "poi_category_mapping", ["poi_category_id"])


def downgrade() -> None:
    op.drop_index("ix_poi_category_mapping_poi_category_id", table_name="poi_category_mapping")
    op.drop_index("ix_point_of_interest_coordinates", table_name="point_of_interest")
    for name in ("ck_poi_radius", "ck_poi_longitude", "ck_poi_latitude"):
        op.drop_constraint(name, "point_of_interest", type_="check")
    op.drop_constraint("uq_point_of_interest_location", "point_of_interest", type_="unique")
