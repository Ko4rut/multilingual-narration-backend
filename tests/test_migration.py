from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import Column

import app.models  # noqa: F401
from app.db import Base


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0001_initial_schema.py"
)


def load_initial_migration():
    spec = spec_from_file_location("initial_schema_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_migration_tables_and_columns_match_orm(monkeypatch):
    migration = load_initial_migration()
    migration_columns = {}

    def capture_table(table_name, *elements, **_kwargs):
        migration_columns[table_name] = {
            element.name for element in elements if isinstance(element, Column)
        }

    monkeypatch.setattr(migration.op, "create_table", capture_table)
    monkeypatch.setattr(migration.op, "create_index", lambda *_args, **_kwargs: None)

    migration.upgrade()

    orm_columns = {
        table_name: set(table.columns.keys())
        for table_name, table in Base.metadata.tables.items()
    }
    assert migration_columns == orm_columns
