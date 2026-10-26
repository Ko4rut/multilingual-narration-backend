import app.models  # noqa: F401
from app.db import Base
from sqlalchemy import CheckConstraint, String, UniqueConstraint, Uuid


EXPECTED_COLUMNS = {
    "action": {"id", "name"},
    "management_function": {"id", "name", "description"},
    "permission": {"id", "function_id", "action_id"},
    "role_permission": {"permission_id", "role_id"},
    "role": {
        "id",
        "name",
        "description",
        "created_by",
        "last_updated_by",
        "created_at",
        "last_updated_at",
    },
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
        for column in Base.metadata.tables["poi_category_mapping"].primary_key.columns
    } == {"poi_id", "poi_category_id"}


def test_cross_domain_foreign_keys_are_registered():
    expected_targets = {
        ("role", "created_by"): "manager_user.id",
        ("role", "last_updated_by"): "manager_user.id",
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
        foreign_keys = (
            Base.metadata.tables[table_name].columns[column_name].foreign_keys
        )
        assert {foreign_key.target_fullname for foreign_key in foreign_keys} == {target}


def test_identifier_types_match_database_design():
    uuid_columns = {
        ("listening_history", "installation_id"),
        ("audit_log", "id"),
    }
    varchar_columns = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.name == "id" or column.name.endswith("_id")
    } - uuid_columns

    for table_name, column_name in uuid_columns:
        assert isinstance(
            Base.metadata.tables[table_name].columns[column_name].type,
            Uuid,
        )
    for table_name, column_name in varchar_columns:
        assert isinstance(
            Base.metadata.tables[table_name].columns[column_name].type,
            String,
        )


def test_identity_model_nullability_and_permission_constraints():
    role = Base.metadata.tables["role"]
    management_function = Base.metadata.tables["management_function"]
    manager_user = Base.metadata.tables["manager_user"]
    permission = Base.metadata.tables["permission"]

    assert role.c.description.nullable
    assert role.c.created_by.nullable
    assert role.c.last_updated_by.nullable
    assert role.c.last_updated_at.nullable
    assert management_function.c.description.nullable
    assert not manager_user.c.last_updated_at.nullable
    assert not any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"function_id", "action_id"}
        for constraint in permission.constraints
    )


def test_identity_status_session_constraints_and_indexes():
    manager_user = Base.metadata.tables["manager_user"]
    user_session = Base.metadata.tables["user_session"]
    role_permission = Base.metadata.tables["role_permission"]

    assert manager_user.c.user_status.type.name == "manager_user_status"
    assert manager_user.c.user_status.type.enums == ["ACTIVE", "INACTIVE"]
    assert {
        constraint.name
        for constraint in user_session.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "ck_user_session_expires_after_creation",
        "ck_user_session_revoked_after_creation",
    }
    assert "ix_user_session_expires_at" in {
        index.name for index in user_session.indexes
    }
    assert "ix_role_permission_role_id" in {
        index.name for index in role_permission.indexes
    }
