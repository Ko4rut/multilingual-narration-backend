from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.listening.exceptions import (
    InvalidListeningEvent,
    ListeningEventConflict,
    ListeningReferenceNotFound,
)
from app.domains.listening.models import ListeningHistory
from app.domains.listening.schemas import ListeningEventCreate
from app.domains.listening.services import ListeningService


def payload(**changes):
    values = {
        "id": "listen-091126-1234abcd",
        "installation_id": UUID("c0a80121-7ac0-4f20-90a0-52df3b17e901"),
        "poi_id": "poi-091126-1234abcd",
        "poi_content_id": "cont-091126-1234abcd",
        "trigger_type": "AUTO_LOCATION",
        "started_at": datetime(2026, 11, 9, 3, tzinfo=timezone.utc),
    }
    values.update(changes)
    return ListeningEventCreate(**values)


def stored_event(**changes):
    values = payload().model_dump()
    values["trigger_type"] = values["trigger_type"].value
    values.update(
        completed_at=None,
        duration_sec=None,
        created_at=datetime(2026, 11, 9, 3, tzinfo=timezone.utc),
    )
    values.update(changes)
    return ListeningHistory(**values)


class SessionStub:
    def __init__(self):
        self.flush_error = None

    def begin(self):
        return nullcontext()

    def flush(self):
        if self.flush_error is not None:
            error = self.flush_error
            self.flush_error = None
            raise error


class RepositoryStub:
    def __init__(self):
        self.event = None
        self.poi_found = True
        self.content = SimpleNamespace(poi_id=payload().poi_id)

    def get_by_id(self, event_id, *, for_update=False):
        return self.event

    def poi_exists(self, poi_id):
        return self.poi_found

    def get_content(self, content_id):
        return self.content

    def add(self, event):
        self.event = event


def build_service(repository=None, session=None):
    repository = repository or RepositoryStub()
    session = session or SessionStub()
    return ListeningService(session, repository), repository, session


def test_create_event_uses_server_created_at():
    service, repository, _session = build_service()

    ack = service.save_event(payload(duration_sec=12))

    assert ack.result.value == "CREATED"
    assert repository.event.duration_sec == 12
    assert repository.event.created_at.tzinfo is timezone.utc


def test_retry_same_event_is_unchanged():
    repository = RepositoryStub()
    repository.event = stored_event(duration_sec=15)
    service, _repository, _session = build_service(repository)

    ack = service.save_event(payload(duration_sec=15))

    assert ack.result.value == "UNCHANGED"


def test_completion_and_duration_only_move_forward():
    completed = datetime(2026, 11, 9, 3, 5, tzinfo=timezone.utc)
    repository = RepositoryStub()
    repository.event = stored_event(duration_sec=20)
    service, _repository, _session = build_service(repository)

    updated = service.save_event(
        payload(duration_sec=45, completed_at=completed)
    )
    stale = service.save_event(
        payload(
            duration_sec=30,
            completed_at=datetime(2026, 11, 9, 3, 4, tzinfo=timezone.utc),
        )
    )
    null_retry = service.save_event(payload())

    assert updated.result.value == "UPDATED"
    assert stale.result.value == "UNCHANGED"
    assert null_retry.result.value == "UNCHANGED"
    assert repository.event.duration_sec == 45
    assert repository.event.completed_at == completed


@pytest.mark.parametrize(
    "changes",
    [
        {"installation_id": UUID("861b4d17-791d-4cf0-8994-d87de64c8093")},
        {"poi_id": "poi-other"},
        {"poi_content_id": "cont-other"},
        {"trigger_type": "QR_CODE"},
        {"started_at": datetime(2026, 11, 9, 3, 1, tzinfo=timezone.utc)},
    ],
)
def test_same_id_with_different_identifying_data_conflicts(changes):
    repository = RepositoryStub()
    repository.event = stored_event()
    service, _repository, _session = build_service(repository)

    with pytest.raises(ListeningEventConflict):
        service.save_event(payload(**changes))


def test_missing_poi_or_content_is_not_found():
    repository = RepositoryStub()
    repository.poi_found = False
    service, _repository, _session = build_service(repository)
    with pytest.raises(ListeningReferenceNotFound, match="POI not found"):
        service.save_event(payload())

    repository.poi_found = True
    repository.content = None
    with pytest.raises(ListeningReferenceNotFound, match="POI content not found"):
        service.save_event(payload(id="listen-091126-5678abcd"))


def test_content_must_belong_to_poi():
    repository = RepositoryStub()
    repository.content = SimpleNamespace(poi_id="poi-other")
    service, _repository, _session = build_service(repository)

    with pytest.raises(InvalidListeningEvent):
        service.save_event(payload())


class ConstraintDiagnostic:
    def __init__(self, constraint_name):
        self.constraint_name = constraint_name


class DuplicatePrimaryKey(Exception):
    diag = ConstraintDiagnostic("listening_history_pkey")


def test_primary_key_race_reconciles_same_event():
    repository = RepositoryStub()
    session = SessionStub()
    session.flush_error = IntegrityError("insert", {}, DuplicatePrimaryKey())
    service, _repository, _session = build_service(repository, session)

    ack = service.save_event(payload())

    assert ack.result.value == "UNCHANGED"


def test_unrelated_integrity_error_is_not_swallowed():
    repository = RepositoryStub()
    session = SessionStub()
    session.flush_error = IntegrityError("insert", {}, Exception("other"))
    service, _repository, _session = build_service(repository, session)

    with pytest.raises(IntegrityError):
        service.save_event(payload())


@pytest.mark.parametrize(
    ("constraint_name", "message"),
    [
        ("listening_history_poi_id_fkey", "POI not found"),
        ("listening_history_poi_content_id_fkey", "POI content not found"),
    ],
)
def test_reference_deleted_during_insert_is_not_found(constraint_name, message):
    class ForeignKeyViolation(Exception):
        diag = ConstraintDiagnostic(constraint_name)

    repository = RepositoryStub()
    session = SessionStub()
    session.flush_error = IntegrityError("insert", {}, ForeignKeyViolation())
    service, _repository, _session = build_service(repository, session)

    with pytest.raises(ListeningReferenceNotFound, match=message):
        service.save_event(payload())
