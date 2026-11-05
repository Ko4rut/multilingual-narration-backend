"""Schema-alignment migration and PostgreSQL enum query regression tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import BigInteger
from sqlalchemy.dialects import postgresql

from app.domains.poi.repositories.poi_content import PoiContentRepository


MIGRATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "alembic" / "versions" / "0007_align_poi_schema.py"
)


def test_migration_has_parent_and_complete_poi_schema_operations(monkeypatch):
    spec = spec_from_file_location("poi_alignment_migration", MIGRATION_FILE)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.revision == "0007_poi_schema_alignment"
    assert module.down_revision == "0006_offline_contract"

    recorded = {"unique": [], "check": [], "index": [], "alter": [], "sql": []}
    monkeypatch.setattr(module.op, "create_unique_constraint",
                        lambda name, *_args, **_kwargs: recorded["unique"].append(name))
    monkeypatch.setattr(module.op, "create_check_constraint",
                        lambda name, *_args, **_kwargs: recorded["check"].append(name))
    monkeypatch.setattr(module.op, "create_index",
                        lambda name, *_args, **_kwargs: recorded["index"].append(name))
    monkeypatch.setattr(module.op, "alter_column",
                        lambda table, name, **kwargs: recorded["alter"].append((table, name, kwargs)))
    monkeypatch.setattr(module.op, "execute",
                        lambda sql: recorded["sql"].append(str(sql)))
    module.upgrade()

    assert set(recorded["unique"]) == {
        "uq_point_of_interest_location", "uq_content_audio_content",
    }
    assert set(recorded["check"]) == {
        "ck_poi_latitude", "ck_poi_longitude", "ck_poi_radius",
        "ck_poi_content_version", "ck_poi_content_status",
        "ck_poi_content_approved_at", "ck_poi_content_published_at",
        "ck_content_audio_size", "ck_content_audio_duration",
        "ck_content_audio_source",
    }
    assert set(recorded["index"]) == {
        "ix_point_of_interest_coordinates",
        "ix_poi_category_mapping_poi_category_id",
        "ix_poi_content_distribution",
        "uq_poi_content_published_language",
        "ix_content_audio_audio_source_type",
    }
    assert len(recorded["alter"]) == 1
    table, name, kwargs = recorded["alter"][0]
    assert (table, name) == ("content_audio", "audio_size")
    assert isinstance(kwargs["type_"], BigInteger)
    assert any("multiple PUBLISHED" in sql for sql in recorded["sql"])
    assert any("duplicate poi_location" in sql for sql in recorded["sql"])
    assert any("multiple audio rows" in sql for sql in recorded["sql"])


def test_published_narration_query_compares_language_enum_without_lower():
    class RecordingSession:
        def __init__(self):
            self.query = None

        def scalars(self, query):
            self.query = query
            return []

    session = RecordingSession()
    repository = PoiContentRepository(session)
    assert repository.get_published_for_language("poi-1", "vi") == []
    sql = str(session.query.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "language.language_status = 'SUPPORTED'" in sql
    assert "lower(language.language_status)" not in sql
    assert "upper(poi_content.content_status)" in sql
