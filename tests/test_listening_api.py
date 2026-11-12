from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.domains.listening.exceptions import (
    InvalidListeningEvent,
    ListeningEventConflict,
    ListeningReferenceNotFound,
)
from app.domains.listening.routers.listening import get_listening_service
from app.domains.listening.schemas import (
    ListeningEventAck,
    ListeningDashboardSummary,
    ListeningSaveResult,
    QrScanAck,
)
from app.domains.identity.routers.dependencies import (
    get_authentication_service,
    get_current_identity,
    require_listening_analytics_read,
)
from app.main import create_app


VALID_EVENT = {
    "id": "listen-091126-1234abcd",
    "installation_id": "c0a80121-7ac0-4f20-90a0-52df3b17e901",
    "poi_id": "poi-091126-1234abcd",
    "poi_content_id": "cont-091126-1234abcd",
    "trigger_type": "AUTO_LOCATION",
    "started_at": "2026-11-09T10:00:00+07:00",
}
VALID_QR_SCAN = {
    "id": "listen-091126-5678abcd",
    "installation_id": "c0a80121-7ac0-4f20-90a0-52df3b17e901",
    "qr_code": "museum-qr",
    "poi_content_id": "cont-091126-1234abcd",
    "scanned_at": "2026-11-09T10:00:00+07:00",
}


class ListeningServiceStub:
    def __init__(self):
        self.error = None
        self.payload = None
        self.qr_payload = None
        self.total_listening_sessions = 42

    def get_dashboard_summary(self):
        return ListeningDashboardSummary(
            total_listening_sessions=self.total_listening_sessions
        )

    def save_event(self, payload):
        self.payload = payload
        if self.error is not None:
            raise self.error
        return ListeningEventAck(id=payload.id, result=ListeningSaveResult.CREATED)

    def save_qr_scan(self, payload):
        self.qr_payload = payload
        if self.error is not None:
            raise self.error
        return QrScanAck(
            id=payload.id,
            result=ListeningSaveResult.CREATED,
            poi_id="poi-091126-1234abcd",
            poi_content_id=payload.poi_content_id,
        )


@pytest.fixture
def listening_client():
    service = ListeningServiceStub()
    application = create_app()
    application.dependency_overrides[get_listening_service] = lambda: service
    application.dependency_overrides[require_listening_analytics_read] = (
        lambda: SimpleNamespace()
    )
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


def test_dashboard_returns_total_listening_sessions(listening_client):
    client, service = listening_client
    service.total_listening_sessions = 123

    response = client.get("/api/v1/listening/dashboard")

    assert response.status_code == 200
    assert response.json() == {"total_listening_sessions": 123}


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


def test_save_qr_scan_returns_resolved_poi_and_normalizes_utc(listening_client):
    client, service = listening_client

    response = client.post("/api/v1/listening/qr-scans", json=VALID_QR_SCAN)

    assert response.status_code == 200
    assert response.json() == {
        "id": VALID_QR_SCAN["id"],
        "result": "CREATED",
        "poi_id": "poi-091126-1234abcd",
        "poi_content_id": VALID_QR_SCAN["poi_content_id"],
    }
    assert service.qr_payload.scanned_at.isoformat() == "2026-11-09T03:00:00+00:00"


@pytest.mark.parametrize(
    "changes",
    [
        {"qr_code": "   "},
        {"scanned_at": "2026-11-09T10:00:00"},
        {"trigger_type": "MANUAL"},
    ],
)
def test_save_qr_scan_rejects_invalid_payload(listening_client, changes):
    client, _service = listening_client

    response = client.post(
        "/api/v1/listening/qr-scans",
        json={**VALID_QR_SCAN, **changes},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ListeningReferenceNotFound("Active POI for QR code not found"), 404),
        (ListeningEventConflict("conflict"), 409),
        (InvalidListeningEvent("mismatch"), 422),
    ],
)
def test_save_qr_scan_maps_domain_errors(listening_client, error, status_code):
    client, service = listening_client
    service.error = error

    response = client.post("/api/v1/listening/qr-scans", json=VALID_QR_SCAN)

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}

class PermissionServiceStub:
    def __init__(self, *, allowed: bool):
        self.allowed = allowed
        self.calls = []

    def has_permission(self, user_id, *, function_name, action_name):
        self.calls.append((user_id, function_name, action_name))
        return self.allowed


def test_dashboard_returns_401_without_bearer_token():
    application = create_app()
    permission_service = PermissionServiceStub(allowed=True)
    application.dependency_overrides[get_listening_service] = ListeningServiceStub
    application.dependency_overrides[get_authentication_service] = (
        lambda: permission_service
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/listening/dashboard")

    assert response.status_code == 401
    assert permission_service.calls == []


@pytest.mark.parametrize(("allowed", "expected_status"), [(True, 200), (False, 403)])
def test_dashboard_checks_seeded_listening_analytics_read_permission(
    allowed, expected_status
):
    application = create_app()
    permission_service = PermissionServiceStub(allowed=allowed)
    application.dependency_overrides[get_listening_service] = ListeningServiceStub
    application.dependency_overrides[get_current_identity] = (
        lambda: SimpleNamespace(manager_user=SimpleNamespace(id="user-test"))
    )
    application.dependency_overrides[get_authentication_service] = (
        lambda: permission_service
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/listening/dashboard")

    assert response.status_code == expected_status
    assert permission_service.calls == [
        ("user-test", "Listening Analytics", "read")
    ]
    if allowed:
        assert response.json() == {"total_listening_sessions": 42}
    else:
        assert response.json() == {"detail": "Insufficient permission"}
