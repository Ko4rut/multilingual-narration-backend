"""Align identifier types with the database design document.

Revision ID: 0002_align_identifier_types
Revises: 0001_initial_schema
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_align_identifier_types"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


FOREIGN_KEYS = (
    ("permission_function_id_fkey", "permission", "function_id", "management_function", "id", "RESTRICT"),
    ("permission_action_id_fkey", "permission", "action_id", "action", "id", "RESTRICT"),
    ("role_permission_permission_id_fkey", "role_permission", "permission_id", "permission", "id", "CASCADE"),
    ("role_permission_role_id_fkey", "role_permission", "role_id", "role", "id", "CASCADE"),
    ("manager_user_role_id_fkey", "manager_user", "role_id", "role", "id", "RESTRICT"),
    ("user_session_user_id_fkey", "user_session", "user_id", "manager_user", "id", "CASCADE"),
    ("point_of_interest_region_id_fkey", "point_of_interest", "region_id", "region", "id", "RESTRICT"),
    ("point_of_interest_created_by_fkey", "point_of_interest", "created_by", "manager_user", "id", "RESTRICT"),
    ("point_of_interest_last_updated_by_fkey", "point_of_interest", "last_updated_by", "manager_user", "id", "RESTRICT"),
    ("poi_content_poi_id_fkey", "poi_content", "poi_id", "point_of_interest", "id", "CASCADE"),
    ("poi_content_language_id_fkey", "poi_content", "language_id", "language", "id", "RESTRICT"),
    ("poi_content_created_by_fkey", "poi_content", "created_by", "manager_user", "id", "RESTRICT"),
    ("poi_content_approved_by_fkey", "poi_content", "approved_by", "manager_user", "id", "RESTRICT"),
    ("poi_content_published_by_fkey", "poi_content", "published_by", "manager_user", "id", "RESTRICT"),
    ("content_audio_poi_content_id_fkey", "content_audio", "poi_content_id", "poi_content", "id", "CASCADE"),
    ("listening_history_poi_content_id_fkey", "listening_history", "poi_content_id", "poi_content", "id", "RESTRICT"),
    ("listening_history_poi_id_fkey", "listening_history", "poi_id", "point_of_interest", "id", "RESTRICT"),
    ("poi_category_mapping_poi_id_fkey", "poi_category_mapping", "poi_id", "point_of_interest", "id", "CASCADE"),
    ("poi_category_mapping_poi_category_id_fkey", "poi_category_mapping", "poi_category_id", "poi_category", "id", "CASCADE"),
    ("offline_package_category_id_fkey", "offline_package", "category_id", "poi_category", "id", "RESTRICT"),
    ("offline_package_region_id_fkey", "offline_package", "region_id", "region", "id", "RESTRICT"),
    ("offline_package_language_id_fkey", "offline_package", "language_id", "language", "id", "RESTRICT"),
    ("offline_package_item_package_id_fkey", "offline_package_item", "package_id", "offline_package", "id", "CASCADE"),
    ("offline_package_item_poi_id_fkey", "offline_package_item", "poi_id", "point_of_interest", "id", "RESTRICT"),
    ("offline_package_item_poi_content_id_fkey", "offline_package_item", "poi_content_id", "poi_content", "id", "RESTRICT"),
    ("offline_package_item_audio_id_fkey", "offline_package_item", "audio_id", "content_audio", "id", "RESTRICT"),
    ("audit_log_user_id_fkey", "audit_log", "user_id", "manager_user", "id", "RESTRICT"),
)

VARCHAR_COLUMNS = {
    "action": ("id",),
    "management_function": ("id",),
    "role": ("id",),
    "permission": ("id", "function_id", "action_id"),
    "role_permission": ("permission_id", "role_id"),
    "manager_user": ("id", "role_id"),
    "user_session": ("id", "user_id"),
    "region": ("id",),
    "language": ("id",),
    "poi_category": ("id",),
    "point_of_interest": ("id", "region_id", "created_by", "last_updated_by"),
    "poi_content": ("id", "poi_id", "language_id", "created_by", "approved_by", "published_by"),
    "content_audio": ("id", "poi_content_id"),
    "listening_history": ("id", "poi_content_id", "poi_id"),
    "poi_category_mapping": ("poi_id", "poi_category_id"),
    "offline_package": ("id", "category_id", "region_id", "language_id"),
    "offline_package_item": ("id", "package_id", "poi_id", "poi_content_id", "audio_id"),
    "audit_log": ("user_id", "entity_id"),
}

SERIAL_ID_TABLES = (
    "action",
    "management_function",
    "role",
    "permission",
    "manager_user",
    "user_session",
    "region",
    "language",
    "poi_category",
    "point_of_interest",
    "poi_content",
    "content_audio",
    "listening_history",
    "offline_package",
    "offline_package_item",
    "audit_log",
)


def _drop_foreign_keys() -> None:
    for name, table, *_rest in FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")


def _create_foreign_keys() -> None:
    for name, table, column, referred_table, referred_column, ondelete in FOREIGN_KEYS:
        op.create_foreign_key(
            name,
            table,
            referred_table,
            [column],
            [referred_column],
            ondelete=ondelete,
        )


def _format_audit_entity(table: str, formatted_id: str) -> None:
    op.execute(
        f"UPDATE audit_log AS child SET entity_id = {formatted_id} "
        f"FROM {table} AS parent "
        f"WHERE child.entity_type = '{table}' AND child.entity_id = parent.id"
    )


def _format_existing_identifiers() -> None:
    # Update referencing values first while parent IDs still contain their old numbers.
    op.execute("UPDATE permission SET action_id = 'acts-' || lpad(action_id, 8, '0')")
    _format_audit_entity("action", "'acts-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE action SET id = 'acts-' || lpad(id, 8, '0')")
    op.execute("UPDATE permission SET function_id = 'func-' || lpad(function_id, 8, '0')")
    _format_audit_entity("management_function", "'func-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE management_function SET id = 'func-' || lpad(id, 8, '0')")
    op.execute("UPDATE role_permission SET permission_id = 'perm-' || lpad(permission_id, 8, '0')")
    _format_audit_entity("permission", "'perm-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE permission SET id = 'perm-' || lpad(id, 8, '0')")
    op.execute("UPDATE role_permission SET role_id = 'role-' || lpad(role_id, 8, '0')")
    op.execute("UPDATE manager_user SET role_id = 'role-' || lpad(role_id, 8, '0')")
    _format_audit_entity("role", "'role-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE role SET id = 'role-' || lpad(id, 8, '0')")

    manager_id = "'user-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')"
    for table, column in (
        ("user_session", "user_id"),
        ("point_of_interest", "created_by"),
        ("point_of_interest", "last_updated_by"),
        ("poi_content", "created_by"),
        ("poi_content", "approved_by"),
        ("poi_content", "published_by"),
        ("audit_log", "user_id"),
    ):
        op.execute(
            f"UPDATE {table} AS child SET {column} = {manager_id} "
            f"FROM manager_user AS parent WHERE child.{column} = parent.id"
        )
    op.execute(
        "UPDATE audit_log AS child SET entity_id = " + manager_id +
        " FROM manager_user AS parent "
        "WHERE child.entity_type = 'manager_user' AND child.entity_id = parent.id"
    )
    op.execute(
        "UPDATE manager_user SET id = 'user-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')"
    )
    _format_audit_entity(
        "user_session",
        "'sess-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')",
    )
    op.execute(
        "UPDATE user_session SET id = 'sess-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')"
    )

    for table, column in (("point_of_interest", "region_id"), ("offline_package", "region_id")):
        op.execute(f"UPDATE {table} SET {column} = 'region-' || lpad({column}, 8, '0')")
    _format_audit_entity("region", "'region-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE region SET id = 'region-' || lpad(id, 8, '0')")
    for table, column in (("poi_content", "language_id"), ("offline_package", "language_id")):
        op.execute(f"UPDATE {table} SET {column} = 'lang-' || lpad({column}, 8, '0')")
    _format_audit_entity("language", "'lang-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE language SET id = 'lang-' || lpad(id, 8, '0')")
    for table, column in (("poi_category_mapping", "poi_category_id"), ("offline_package", "category_id")):
        op.execute(f"UPDATE {table} SET {column} = 'cat-' || lpad({column}, 8, '0') WHERE {column} IS NOT NULL")
    _format_audit_entity("poi_category", "'cat-' || lpad(parent.id, 8, '0')")
    op.execute("UPDATE poi_category SET id = 'cat-' || lpad(id, 8, '0')")

    poi_id = "'poi-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')"
    for table, column in (
        ("poi_category_mapping", "poi_id"),
        ("poi_content", "poi_id"),
        ("listening_history", "poi_id"),
        ("offline_package_item", "poi_id"),
    ):
        op.execute(
            f"UPDATE {table} AS child SET {column} = {poi_id} "
            f"FROM point_of_interest AS parent WHERE child.{column} = parent.id"
        )
    op.execute(
        "UPDATE audit_log AS child SET entity_id = " + poi_id +
        " FROM point_of_interest AS parent "
        "WHERE child.entity_type = 'point_of_interest' AND child.entity_id = parent.id"
    )
    op.execute("UPDATE point_of_interest SET id = 'poi-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')")

    content_id = "'cont-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')"
    for table, column in (
        ("content_audio", "poi_content_id"),
        ("listening_history", "poi_content_id"),
        ("offline_package_item", "poi_content_id"),
    ):
        op.execute(
            f"UPDATE {table} AS child SET {column} = {content_id} "
            f"FROM poi_content AS parent WHERE child.{column} = parent.id"
        )
    op.execute(
        "UPDATE audit_log AS child SET entity_id = " + content_id +
        " FROM poi_content AS parent "
        "WHERE child.entity_type = 'poi_content' AND child.entity_id = parent.id"
    )
    op.execute("UPDATE poi_content SET id = 'cont-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')")

    audio_id = "'audio-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')"
    op.execute(
        "UPDATE offline_package_item AS child SET audio_id = " + audio_id +
        " FROM content_audio AS parent WHERE child.audio_id = parent.id"
    )
    _format_audit_entity("content_audio", audio_id)
    op.execute(
        "UPDATE content_audio SET id = 'audio-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')"
    )
    package_id = "'pack-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')"
    op.execute(
        "UPDATE offline_package_item AS child SET package_id = " + package_id +
        " FROM offline_package AS parent WHERE child.package_id = parent.id"
    )
    _format_audit_entity("offline_package", package_id)
    op.execute("UPDATE offline_package SET id = 'pack-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')")
    _format_audit_entity(
        "offline_package_item",
        "'pack-item-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')",
    )
    op.execute("UPDATE offline_package_item SET id = 'pack-item-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')")
    _format_audit_entity(
        "listening_history",
        "'listen-' || to_char(parent.created_at, 'DDMMYY') || '-' || lpad(parent.id, 8, '0')",
    )
    op.execute(
        "UPDATE listening_history SET id = 'listen-' || to_char(created_at, 'DDMMYY') || '-' || lpad(id, 8, '0')"
    )


def upgrade() -> None:
    _drop_foreign_keys()

    for table in SERIAL_ID_TABLES:
        op.alter_column(
            table,
            "id",
            existing_type=sa.Integer(),
            server_default=None,
        )
        op.execute(f"DROP SEQUENCE IF EXISTS {table}_id_seq")

    for table, columns in VARCHAR_COLUMNS.items():
        for column in columns:
            op.alter_column(
                table,
                column,
                existing_type=sa.Integer(),
                type_=sa.String(length=50),
                postgresql_using=f"{column}::text",
            )

    uuid_type = postgresql.UUID(as_uuid=True)
    op.alter_column(
        "audit_log",
        "id",
        existing_type=sa.Integer(),
        type_=uuid_type,
        postgresql_using="md5('audit_log:' || id::text)::uuid",
    )
    op.alter_column(
        "listening_history",
        "installation_id",
        existing_type=sa.String(length=100),
        type_=uuid_type,
        postgresql_using=(
            "CASE WHEN installation_id ~* "
            "'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' "
            "THEN installation_id::uuid "
            "ELSE md5('installation:' || installation_id)::uuid END"
        ),
    )

    _format_existing_identifiers()
    _create_foreign_keys()


def downgrade() -> None:
    raise RuntimeError(
        "Identifier migration is irreversible after varchar/UUID IDs are in use"
    )
