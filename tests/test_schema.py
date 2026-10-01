from app.db import Base
import app.models  # noqa: F401


def test_expected_tables_are_present():
    expected = {
        "audit_log", "action", "management_function", "permission", "role_permission", "role",
        "management_user", "point_of_interest", "poi_content", "content_audio", "listening_history",
        "poi_category", "poi_category_mapping", "region", "language", "offline_package",
    }
    assert expected == set(Base.metadata.tables)


def test_composite_primary_keys():
    assert {c.name for c in Base.metadata.tables["role_permission"].primary_key.columns} == {"role_id", "permission_id"}
    assert {c.name for c in Base.metadata.tables["poi_category_mapping"].primary_key.columns} == {"poi_id", "poi_category_id"}
