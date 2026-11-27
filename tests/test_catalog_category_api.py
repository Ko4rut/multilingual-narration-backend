from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.domains.catalog.exceptions import (
    PoiCategoryAlreadyExists,
    PoiCategoryInUse,
    PoiCategoryNotFound,
)
from app.domains.catalog.routers import get_catalog_service
from app.domains.identity.routers.dependencies import get_authentication_service
from app.main import create_app


class AuthStub:
    def __init__(self, *, permitted=True):
        self.permitted = permitted
        self.checks = []

    def authenticate_access_token(self, token):
        return SimpleNamespace(manager_user=SimpleNamespace(id="user-1"))

    def has_permission(self, user_id, *, function_name, action_name):
        self.checks.append((user_id, function_name, action_name))
        return self.permitted


class CategoryServiceStub:
    def __init__(self):
        self.records = [
            SimpleNamespace(id="cat-1", category_name="Museum", category_code="MUSEUM"),
        ]
        self.error = None

    def list_categories(self):
        return self.records

    def create_category(self, **payload):
        if self.error:
            raise self.error
        record = SimpleNamespace(id="cat-2", **payload)
        self.records.append(record)
        return record

    def update_category(self, category_id, **payload):
        if self.error:
            raise self.error
        record = next((item for item in self.records if item.id == category_id), None)
        if record is None:
            raise PoiCategoryNotFound("POI Category not found")
        record.category_name = payload["category_name"]
        return record

    def delete_category(self, category_id):
        if self.error:
            raise self.error
        self.records = [item for item in self.records if item.id != category_id]


@pytest.fixture
def client_factory():
    def create(*, auth=None, service=None):
        app = create_app()
        app.dependency_overrides[get_catalog_service] = lambda: service or CategoryServiceStub()
        authentication = auth if auth is not None else AuthStub()
        app.dependency_overrides[get_authentication_service] = lambda: authentication
        return TestClient(app)
    return create


def test_category_admin_requires_auth(client_factory):
    with client_factory() as client:
        for method, suffix in [
            ("get", ""), ("post", ""), ("patch", "/cat-1"), ("delete", "/cat-1"),
        ]:
            response = getattr(client, method)(
                "/api/v1/admin/catalog/categories" + suffix,
            )
            assert response.status_code == 401


@pytest.mark.parametrize("method,path,body,action", [
    ("get", "/api/v1/admin/catalog/categories", None, "read"),
    ("post", "/api/v1/admin/catalog/categories", {
        "category_name": "Park", "category_code": "park",
    }, "create"),
    ("patch", "/api/v1/admin/catalog/categories/cat-1", {
        "category_name": "Renamed",
    }, "update"),
    ("delete", "/api/v1/admin/catalog/categories/cat-1", None, "delete"),
])
def test_category_admin_checks_poi_management_permission(
    client_factory, method, path, body, action,
):
    auth = AuthStub(permitted=False)
    kwargs = {"headers": {"Authorization": "Bearer test-token"}}
    if body is not None:
        kwargs["json"] = body
    with client_factory(auth=auth) as client:
        response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403
    assert auth.checks == [("user-1", "POI Management", action)]


def test_category_admin_crud_and_public_read(client_factory):
    service = CategoryServiceStub()
    auth = AuthStub()
    headers = {"Authorization": "Bearer test-token"}
    with client_factory(auth=auth, service=service) as client:
        initial = client.get("/api/v1/admin/catalog/categories", headers=headers)
        created = client.post("/api/v1/admin/catalog/categories", headers=headers, json={
            "category_name": "  Art Museum  ", "category_code": "art-museum",
        })
        updated = client.patch("/api/v1/admin/catalog/categories/cat-2",
                               headers=headers, json={"category_name": "Contemporary Art"})
        public = client.get("/api/v1/catalog/categories")
        deleted = client.delete("/api/v1/admin/catalog/categories/cat-2", headers=headers)
        after = client.get("/api/v1/catalog/categories")

    assert initial.status_code == 200
    assert len(initial.json()) == 1
    assert created.status_code == 201
    assert created.json() == {
        "id": "cat-2", "category_name": "Art Museum", "category_code": "art-museum",
    }
    assert updated.status_code == 200
    assert updated.json()["category_name"] == "Contemporary Art"
    assert public.status_code == 200
    assert len(public.json()) == 2
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert len(after.json()) == 1


@pytest.mark.parametrize("method,body", [
    ("post", {"category_name": "Museum", "category_code": "MUSEUM"}),
    ("post", {"category_name": "Museum", "category_code": "art_park"}),
    ("post", {"category_name": "", "category_code": "museum"}),
    ("patch", {}),
    ("patch", {"category_code": "new-code"}),
    ("patch", {"category_name": None}),
])
def test_invalid_category_inputs_return_422(client_factory, method, body):
    path = "/api/v1/admin/catalog/categories"
    if method == "patch":
        path += "/cat-1"
    with client_factory(auth=AuthStub()) as client:
        response = getattr(client, method)(path, headers={
            "Authorization": "Bearer test-token",
        }, json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("method,error,expected", [
    ("post", PoiCategoryAlreadyExists("Already exists"), 409),
    ("patch", PoiCategoryNotFound("Not found"), 404),
    ("patch", PoiCategoryAlreadyExists("Already exists"), 409),
    ("delete", PoiCategoryNotFound("Not found"), 404),
    ("delete", PoiCategoryInUse("Still referenced"), 409),
])
def test_category_business_errors_are_translated(
    client_factory, method, error, expected,
):
    service = CategoryServiceStub()
    service.error = error
    path = "/api/v1/admin/catalog/categories"
    kwargs = {"headers": {"Authorization": "Bearer test-token"}}
    if method == "post":
        kwargs["json"] = {"category_name": "Park", "category_code": "park"}
    else:
        path += "/cat-1"
        if method == "patch":
            kwargs["json"] = {"category_name": "Modern Museum"}
    with client_factory(auth=AuthStub(), service=service) as client:
        response = getattr(client, method)(path, **kwargs)
    assert response.status_code == expected
