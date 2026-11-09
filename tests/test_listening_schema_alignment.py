from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app.domains.listening.models import ListeningHistory


MIGRATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0008_add_listening_event_constraints.py"
)


def test_listening_model_declares_documented_constraints_and_indexes():
    constraints = {constraint.name for constraint in ListeningHistory.__table__.constraints}
    indexes = {index.name for index in ListeningHistory.__table__.indexes}

    assert {
        "ck_listening_history_trigger_type",
        "ck_listening_history_duration_nonnegative",
        "ck_listening_history_completed_after_started",
    } <= constraints
    assert {
        "ix_listening_history_poi_started_at",
        "ix_listening_history_installation_started_at",
    } <= indexes


def test_migration_preserves_legacy_rows_and_adds_new_write_guards(monkeypatch):
    spec = spec_from_file_location("listening_migration", MIGRATION_FILE)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    recorded = {"sql": [], "indexes": []}
    monkeypatch.setattr(
        module.op,
        "execute",
        lambda sql: recorded["sql"].append(str(sql)),
    )
    monkeypatch.setattr(
        module.op,
        "create_index",
        lambda name, *_args, **_kwargs: recorded["indexes"].append(name),
    )

    module.upgrade()

    assert module.down_revision == "0007_poi_schema_alignment"
    assert len(recorded["sql"]) == 3
    assert all("NOT VALID" in sql for sql in recorded["sql"])
    assert set(recorded["indexes"]) == {
        "ix_listening_history_poi_started_at",
        "ix_listening_history_installation_started_at",
    }
