from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import Column

import app.models  # noqa: F401
from app.db import Base


MIGRATIONS_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def load_migration(filename: str):
    path = MIGRATIONS_PATH / filename
    spec = spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_chain_tables_and_columns_match_orm(monkeypatch):
    initial_migration = load_migration("0001_initial_schema.py")
    identity_migration = load_migration("0003_update_identity_models.py")
    migration_columns = {}

    def capture_table(table_name, *elements, **_kwargs):
        migration_columns[table_name] = {
            element.name for element in elements if isinstance(element, Column)
        }

    monkeypatch.setattr(initial_migration.op, "create_table", capture_table)
    monkeypatch.setattr(
        initial_migration.op,
        "create_index",
        lambda *_args, **_kwargs: None,
    )

    initial_migration.upgrade()

    def capture_column(table_name, column):
        migration_columns[table_name].add(column.name)

    monkeypatch.setattr(identity_migration.op, "add_column", capture_column)
    monkeypatch.setattr(
        identity_migration.op,
        "alter_column",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        identity_migration.op,
        "create_foreign_key",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        identity_migration.op,
        "drop_constraint",
        lambda *_args, **_kwargs: None,
    )

    identity_migration.upgrade()

    orm_columns = {
        table_name: set(table.columns.keys())
        for table_name, table in Base.metadata.tables.items()
    }
    assert migration_columns == orm_columns
