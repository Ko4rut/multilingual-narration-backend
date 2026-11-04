from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.domains.catalog.exceptions import LanguageAlreadyExists, LanguageInUse, LanguageNotFound
from app.domains.catalog.models import LanguageStatus
from app.domains.catalog.routers import get_catalog_service
from app.domains.catalog.services import CatalogService
from app.domains.identity.routers.dependencies import get_authentication_service
from app.main import create_app


class CatalogRepositoryStub:
    def __init__(self, records):
        self.records = records

    def list_all(self):
        return self.records

    def list_supported(self):
        return [
            record
            for record in self.records
            if record.language_status == LanguageStatus.SUPPORTED
        ]


class SessionStub:
    pass


class AuthenticationServiceStub:
    def __init__(self, *, permitted=True):
        self.permitted = permitted
        self.permission_checks = []

    def authenticate_access_token(self, token):
        return SimpleNamespace(manager_user=SimpleNamespace(id="user-1"))

    def has_permission(self, user_id, *, function_name, action_name):
        self.permission_checks.append((user_id, function_name, action_name))
        return self.permitted


@pytest.fixture
def catalog_client_factory():
    def build(*, regions=None, categories=None, languages=None, auth=None, service=None):
        application = create_app()
        service = service or CatalogService(
            session=SessionStub(),
            language_repository=CatalogRepositoryStub(languages or []),
            region_repository=CatalogRepositoryStub(regions or []),
            poi_category_repository=CatalogRepositoryStub(categories or []),
        )
        application.dependency_overrides[get_catalog_service] = lambda: service
        if auth is not None:
            application.dependency_overrides[get_authentication_service] = lambda: auth
        return TestClient(application)

    return build


def test_list_regions_is_public_and_returns_declared_fields_in_order(
    catalog_client_factory,
):
    regions = [
        SimpleNamespace(id="region-00000001", region_name="North", region_code="north"),
        SimpleNamespace(id="region-00000002", region_name="South", region_code="south"),
    ]

    with catalog_client_factory(regions=regions) as client:
        response = client.get("/api/v1/catalog/regions")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "region-00000001", "region_name": "North", "region_code": "north"},
        {"id": "region-00000002", "region_name": "South", "region_code": "south"},
    ]


def test_list_categories_is_public_and_returns_declared_fields_in_order(
    catalog_client_factory,
):
    categories = [
        SimpleNamespace(id="cat-00000001", category_name="Museum", category_code="museum"),
        SimpleNamespace(id="cat-00000002", category_name="Nature", category_code="nature"),
    ]

    with catalog_client_factory(categories=categories) as client:
        response = client.get("/api/v1/catalog/categories")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "cat-00000001", "category_name": "Museum", "category_code": "museum"},
        {"id": "cat-00000002", "category_name": "Nature", "category_code": "nature"},
    ]


@pytest.mark.parametrize("path", ["regions", "categories"])
def test_catalog_list_returns_empty_array(catalog_client_factory, path):
    with catalog_client_factory() as client:
        response = client.get(f"/api/v1/catalog/{path}")

    assert response.status_code == 200
    assert response.json() == []


def language(
    language_id,
    language_code,
    language_name,
    language_status,
):
    return SimpleNamespace(
        id=language_id,
        language_code=language_code,
        language_name=language_name,
        language_status=language_status,
    )


def test_public_languages_returns_only_supported_without_token(catalog_client_factory):
    languages = [
        language("lang-00000001", "en", "English", LanguageStatus.SUPPORTED),
        language("lang-00000002", "fr", "French", LanguageStatus.UNSUPPORTED),
    ]
    with catalog_client_factory(languages=languages) as client:
        response = client.get("/api/v1/catalog/languages")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "lang-00000001",
            "language_code": "en",
            "language_name": "English",
            "language_status": "SUPPORTED",
        }
    ]


def test_admin_languages_requires_authentication(catalog_client_factory):
    with catalog_client_factory() as client:
        response = client.get("/api/v1/admin/catalog/languages")
    assert response.status_code == 401


def test_admin_languages_requires_dynamic_permission(catalog_client_factory):
    auth = AuthenticationServiceStub(permitted=False)
    with catalog_client_factory(auth=auth) as client:
        response = client.get(
            "/api/v1/admin/catalog/languages", headers={"Authorization": "Bearer token"}
        )
    assert response.status_code == 403
    assert auth.permission_checks == [("user-1", "Language Management", "read")]


class LanguageServiceStub:
    def __init__(self):
        self.record = language("lang-12345678", "en", "English", LanguageStatus.SUPPORTED)
        self.error = None

    def list_languages(self):
        return [self.record]

    def create_language(self, **payload):
        if self.error:
            raise self.error
        return language("lang-12345678", **payload)

    def update_language(self, language_id, **payload):
        if self.error:
            raise self.error
        values = {
            "language_code": self.record.language_code,
            "language_name": self.record.language_name,
            "language_status": self.record.language_status,
            **payload,
        }
        return language(language_id, **values)

    def delete_language(self, language_id):
        if self.error:
            raise self.error


def test_admin_language_crud_contract(catalog_client_factory):
    service = LanguageServiceStub()
    auth = AuthenticationServiceStub()
    headers = {"Authorization": "Bearer token"}
    with catalog_client_factory(service=service, auth=auth) as client:
        listed = client.get("/api/v1/admin/catalog/languages", headers=headers)
        created = client.post(
            "/api/v1/admin/catalog/languages",
            headers=headers,
            json={"language_code": " EN ", "language_name": " English ", "language_status": "SUPPORTED"},
        )
        updated = client.patch(
            "/api/v1/admin/catalog/languages/lang-12345678",
            headers=headers,
            json={"language_name": "Modern English"},
        )
        deleted = client.delete(
            "/api/v1/admin/catalog/languages/lang-12345678", headers=headers
        )
    assert listed.status_code == 200
    assert created.status_code == 201
    assert created.json()["language_code"] == "en"
    assert created.json()["language_name"] == "English"
    assert updated.status_code == 200
    assert updated.json()["language_name"] == "Modern English"
    assert deleted.status_code == 204 and deleted.content == b""
    assert [check[2] for check in auth.permission_checks] == ["read", "create", "update", "delete"]


@pytest.mark.parametrize(
    ("method", "body"),
    [
        ("post", {"language_code": "cmn", "language_name": "Name", "language_status": "SUPPORTED"}),
        ("post", {"language_code": "en", "language_name": " ", "language_status": "SUPPORTED"}),
        ("patch", {}),
        ("patch", {"language_name": None}),
        ("patch", {"language_code": "fr"}),
    ],
)
def test_language_input_validation_returns_422(catalog_client_factory, method, body):
    auth = AuthenticationServiceStub()
    path = "/api/v1/admin/catalog/languages"
    if method == "patch":
        path += "/lang-12345678"
    with catalog_client_factory(service=LanguageServiceStub(), auth=auth) as client:
        response = getattr(client, method)(path, headers={"Authorization": "Bearer token"}, json=body)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "error", "expected"),
    [
        ("post", LanguageAlreadyExists("duplicate"), 409),
        ("patch", LanguageNotFound("missing"), 404),
        ("patch", LanguageAlreadyExists("duplicate"), 409),
        ("delete", LanguageNotFound("missing"), 404),
        ("delete", LanguageInUse("used"), 409),
    ],
)
def test_language_errors_are_mapped(catalog_client_factory, method, error, expected):
    service = LanguageServiceStub()
    service.error = error
    auth = AuthenticationServiceStub()
    path = "/api/v1/admin/catalog/languages"
    kwargs = {"headers": {"Authorization": "Bearer token"}}
    if method == "post":
        kwargs["json"] = {"language_code": "en", "language_name": "English", "language_status": "SUPPORTED"}
    else:
        path += "/lang-12345678"
        if method == "patch":
            kwargs["json"] = {"language_name": "English 2"}
    with catalog_client_factory(service=service, auth=auth) as client:
        response = getattr(client, method)(path, **kwargs)
    assert response.status_code == expected
