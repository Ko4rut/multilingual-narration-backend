from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.domains.poi.router import get_poi_service
from app.domains.poi.service import PoiService
from app.main import create_app


class PoiRepositoryStub:
    def list_active(self, *, offset, limit):
        return [self.poi][offset:offset + limit]

    def get_active(self, poi_id):
        return self.poi if poi_id == self.poi.id else None

    poi = SimpleNamespace(
        id=1, region_id=1, poi_name="Museum", image_url=None, qr_code="museum",
        poi_priority=1, latitude="10.000000", longitude="106.000000",
        trigger_radius="50.00", poi_location="City", is_active=True,
        created_by=123,
    )


@pytest.fixture
def client():
    application = create_app()
    application.dependency_overrides[get_poi_service] = lambda: PoiService(PoiRepositoryStub())
    with TestClient(application) as client:
        yield client


def test_health_without_database(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_poi_response_and_pagination(client):
    response = client.get("/api/v1/pois")
    assert response.status_code == 200
    assert response.json()[0]["poi_name"] == "Museum"
    assert "created_by" not in response.json()[0]
    assert client.get("/api/v1/pois?offset=1").json() == []
    assert client.get("/api/v1/pois/1").json() == response.json()[0]


def test_missing_poi_maps_domain_error_to_404(client):
    response = client.get("/api/v1/pois/2")
    assert response.status_code == 404
    assert response.json() == {"detail": "POI not found"}


@pytest.mark.parametrize("path", ["?offset=-1", "?limit=0", "?limit=101", "/0", "/abc"])
def test_invalid_parameters(client, path):
    assert client.get("/api/v1/pois" + path).status_code == 422
