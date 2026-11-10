from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.domains.listening.exceptions import (
    InvalidListeningEvent,
    ListeningEventConflict,
    ListeningReferenceNotFound,
)
from app.domains.listening.routers.listening import get_listening_service
from app.domains.listening.schemas import ListeningEventAck, ListeningSaveResult
from app.main import create_app


VALID_EVENT = {
    "id": "listen-091126-1234abcd",
    "installation_id": "c0a80121-7ac0-4f20-90a0-52df3b17e901",
    "poi_id": "poi-091126-1234abcd",
    "poi_content_id": "cont-091126-1234abcd",
    "trigger_type": "AUTO_LOCATION",
    "started_at": "2026-11-09T10:00:00+07:00",
}


class ListeningServiceStub:
    def __init__(self):
        self.error = None
        self.payload = None

    def save_event(self, payload):
        self.payload = payload
        if self.error is not None:
            raise self.error
        return ListeningEventAck(id=payload.id, result=ListeningSaveResult.CREATED)


@pytest.fixture
def listening_client():
    service = ListeningServiceStub()
    application = create_app()
    application.dependency_overrides[get_listening_service] = lambda: service
    with TestClient(application) as client:
        yield client, service


def test_save_event_is_anonymous_returns_ack_and_normalizes_utc(listening_client):
    client, service = listening_client

    response = client.post("/api/v1/listening/events", json=VALID_EVENT)

    assert response.status_code == 200
    assert response.json() == {
        "id": VALID_EVENT["id"],
        "result": "CREATED",
    }
    assert service.payload.started_at.isoformat() == "2026-11-09T03:00:00+00:00"


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "listen-invalid"},
        {"id": "listen-321326-1234abcd"},
        {"installation_id": "not-a-uuid"},
        {"started_at": "2026-11-09T10:00:00"},
        {"duration_sec": -1},
        {"duration_sec": 1.5},
        {"duration_sec": True},
        {"completed_at": "2026-11-09T09:59:59+07:00"},
        {"created_at": "2026-11-09T10:00:00Z"},
    ],
)
def test_save_event_rejects_invalid_payload(listening_client, changes):
    client, _service = listening_client
    payload = {**VALID_EVENT, **changes}

    response = client.post("/api/v1/listening/events", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ListeningReferenceNotFound("POI not found"), 404),
        (ListeningEventConflict("conflict"), 409),
        (InvalidListeningEvent("mismatch"), 422),
    ],
)
def test_save_event_maps_domain_errors(listening_client, error, status_code):
    client, service = listening_client
    service.error = error

    response = client.post("/api/v1/listening/events", json=VALID_EVENT)

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}
