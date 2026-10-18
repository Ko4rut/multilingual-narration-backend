import app.models  # noqa: F401
from app.db import Base


EXPECTED_COLUMNS = {
    "action": {"id", "name"},
    "management_function": {"id", "name"},
    "permission": {"id", "function_id", "action_id"},
    "role_permission": {"permission_id", "role_id"},
    "role": {"id", "name", "created_at", "last_updated_at"},
    "manager_user": {
        "id",
        "role_id",
        "email",
        "password_hash",
        "full_name",
        "user_status",
        "created_at",
        "last_updated_at",
        "last_login_at",
    },
    "user_session": {
        "id",
        "user_id",
        "refresh_token_hash",
        "expires_at",
        "created_at",
        "revoked_at",
    },
    "audit_log": {
        "id",
        "user_id",
        "action",
        "entity_type",
        "entity_id",
        "old_values",
        "new_values",
        "created_at",
    },
    "region": {"id", "region_name", "region_code"},
    "language": {
        "id",
        "language_code",
        "language_name",
        "language_status",
    },
    "poi_category": {"id", "category_name", "category_code"},
    "point_of_interest": {
        "id",
        "region_id",
        "poi_image_url",
        "image_checksum_sha256",
        "poi_qr_code",
        "poi_name",
        "poi_location",
        "poi_status",
        "latitude",
        "longitude",
        "trigger_radius_meter",
        "created_by",
        "last_updated_by",
        "created_at",
        "last_updated_at",
    },
    "poi_category_mapping": {"poi_id", "poi_category_id"},
    "poi_content": {
        "id",
        "poi_id",
        "language_id",
        "narration_title",
        "narration_script",
        "content_version",
        "content_status",
        "created_by",
        "approved_by",
        "published_by",
        "created_at",
        "approved_at",
        "published_at",
    },
    "content_audio": {
        "id",
        "poi_content_id",
        "audio_url",
        "audio_size",
        "audio_source_type",
        "audio_duration_sec",
        "audio_mime_type",
        "audio_checksum_sha256",
        "created_at",
        "last_updated_at",
    },
    "listening_history": {
        "id",
        "installation_id",
        "poi_content_id",
        "poi_id",
        "trigger_type",
        "started_at",
        "completed_at",
        "duration_sec",
        "created_at",
    },
    "offline_package": {
        "id",
        "category_id",
        "region_id",
        "language_id",
        "package_key",
        "package_name",
        "package_url",
        "package_version",
        "total_size",
        "package_checksum_sha256",
        "package_status",
        "schema_version",
        "created_at",
        "last_updated_at",
        "published_at",
    },
    "offline_package_item": {
        "id",
        "package_id",
        "poi_id",
        "poi_content_id",
        "audio_id",
        "content_version",
        "created_at",
        "last_updated_at",
    },
}


def test_tables_and_columns_match_the_erd():
    assert set(Base.metadata.tables) == set(EXPECTED_COLUMNS)
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == expected_columns


def test_composite_primary_keys():
    assert {
        column.name
        for column in Base.metadata.tables["role_permission"].primary_key.columns
    } == {"role_id", "permission_id"}
    assert {
        column.name
        for column in Base.metadata.tables[
            "poi_category_mapping"
        ].primary_key.columns
    } == {"poi_id", "poi_category_id"}


def test_cross_domain_foreign_keys_are_registered():
    expected_targets = {
        ("manager_user", "role_id"): "role.id",
        ("user_session", "user_id"): "manager_user.id",
        ("point_of_interest", "created_by"): "manager_user.id",
        ("point_of_interest", "last_updated_by"): "manager_user.id",
        ("poi_content", "approved_by"): "manager_user.id",
        ("listening_history", "poi_content_id"): "poi_content.id",
        ("offline_package_item", "package_id"): "offline_package.id",
        ("offline_package_item", "audio_id"): "content_audio.id",
    }
    for (table_name, column_name), target in expected_targets.items():
        foreign_keys = Base.metadata.tables[table_name].columns[
            column_name
        ].foreign_keys
        assert {foreign_key.target_fullname for foreign_key in foreign_keys} == {
            target
        }
