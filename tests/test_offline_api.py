"""HTTP contract tests for Group 3 public and administrative package routes."""

from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.identity.routers.dependencies import (
    get_authentication_service, get_current_identity,
)
from app.domains.offline.models.offline_package import OfflinePackageStatus
from app.domains.offline.routers.dependencies import get_offline_service
from app.domains.offline.schemas.offline_package import OfflinePackagePage
from app.domains.offline.services.offline import (
    OfflinePackageNotFound, OfflinePackagePreparationError, OfflineRebuildPlan,
)
from app.domains.offline.utils.manifest_diff import ManifestChanges
from app.main import create_app


NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def package(*, published=True):
    return SimpleNamespace(
        id="pack-1",
        category_id=None, region_id="region-1", language_id="lang-vi",
        package_key="region:HAN|lang:vi", package_name="Hà Nội (Tiếng Việt)",
        package_url="https://cdn.example.local/manifest/v1.json" if published else None,
        package_version=1, total_size=2048 if published else None,
        package_checksum_sha256="a" * 64 if published else None,
        package_status=(
            OfflinePackageStatus.PUBLISHED if published else OfflinePackageStatus.BUILDING
        ),
        schema_version=1, created_at=NOW, last_updated_at=NOW,
        published_at=NOW if published else None,
    )


@pytest.fixture
def setup():
    app = create_app()
    service = MagicMock()
    service.list_published_packages.return_value = OfflinePackagePage(
        items=[package()], total=1, offset=0, limit=10,
    )
    service.get_published_package.return_value = package()
    service.list_admin_packages.return_value = OfflinePackagePage(
        items=[package(published=False)], total=1, offset=0, limit=20,
    )
    service.get_admin_package.return_value = package(published=False)
    service.get_admin_package_items.return_value = []
    service.prepare_initial_package.return_value = (
        package(published=False),
        b'{"package_key":"region:HAN|lang:vi","items":[]}',
    )
    changes = ManifestChanges(
        added_poi_ids=(), removed_poi_ids=(), updated_poi_ids=(),
        assets_to_download=(), metadata_changed=False,
    )
    service.plan_rebuild.return_value = OfflineRebuildPlan(
        package_id="pack-1", expected_version=1, expected_checksum="a" * 64,
        manifest=None, changes=changes,
    )
    app.dependency_overrides[get_offline_service] = lambda: service
    identity = SimpleNamespace(manager_user=SimpleNamespace(id="admin-1"))
    auth = SimpleNamespace(has_permission=lambda *_args, **_kwargs: True)
    app.dependency_overrides[get_current_identity] = lambda: identity
    app.dependency_overrides[get_authentication_service] = lambda: auth
    with TestClient(app) as client:
        yield client, app, service, auth


def test_swagger_openapi_exposes_offline_paths(setup):
    client, _, _, _ = setup
    spec = client.get("/openapi.json").json()
    assert "/api/v1/offline/packages" in spec["paths"]
    assert "get" in spec["paths"]["/api/v1/offline/packages"]
    assert "/api/v1/offline/packages/{package_id}" in spec["paths"]
    assert "/api/v1/admin/offline/packages" in spec["paths"]
    assert "/api/v1/admin/offline/packages/{package_id}" in spec["paths"]
    assert "/api/v1/admin/offline/packages/{package_id}/items" in spec["paths"]
    assert "/api/v1/admin/offline/packages/prepare" in spec["paths"]
    preview = "/api/v1/admin/offline/packages/{package_id}/rebuild/preview"
    assert "post" in spec["paths"][preview]
    assert "/api/v1/admin/offline/packages/{package_id}/publish" not in spec


def test_public_package_listing_and_detail(setup):
    client, _, service, _ = setup
    response = client.get(
        "/api/v1/offline/packages?region_id=region-1&offset=0&limit=10"
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["package_status"] == "PUBLISHED"
    assert response.json()["total"] == 1
    assert client.get("/api/v1/offline/packages/pack-1").status_code == 200
    service.list_published_packages.assert_called_once_with(
        region_id="region-1", language_id=None, category_id=None,
        offset=0, limit=10,
    )


@pytest.mark.parametrize("query", ("?offset=-1", "?limit=0", "?limit=101", "?region_id="))
def test_public_package_validation(setup, query):
    client, _, _, _ = setup
    assert client.get("/api/v1/offline/packages" + query).status_code == 422


def test_public_detail_hides_unpublished_or_missing_package(setup):
    client, _, service, _ = setup
    service.get_published_package.side_effect = OfflinePackageNotFound(
        "Offline package not found"
    )
    response = client.get("/api/v1/offline/packages/pack-1")
    assert response.status_code == 404
    assert response.json() == {"detail": "Offline package not found"}


def test_admin_package_list_and_items(setup):
    client, _, _, _ = setup
    listed = client.get("/api/v1/admin/offline/packages")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["package_status"] == "BUILDING"
    assert listed.json()["total"] == 1
    assert client.get("/api/v1/admin/offline/packages/pack-1").status_code == 200
    assert client.get("/api/v1/admin/offline/packages/pack-1/items").json() == []


def test_prepare_returns_building_metadata_and_preview(setup):
    client, _, service, _ = setup
    response = client.post(
        "/api/v1/admin/offline/packages/prepare",
        json={"region_id": "region-1", "language_id": "lang-vi"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["package"]["package_status"] == "BUILDING"
    assert response.json()["package"]["package_url"] is None
    assert response.json()["manifest"]["items"] == []
    service.prepare_initial_package.assert_called_once_with(
        region_id="region-1", language_id="lang-vi", category_id=None,
    )


def test_prepare_duplicate_or_invalid_filters(setup):
    client, _, service, _ = setup
    service.prepare_initial_package.side_effect = OfflinePackagePreparationError(
        "Package already exists"
    )
    response = client.post(
        "/api/v1/admin/offline/packages/prepare",
        json={"region_id": "region-1", "language_id": "lang-vi"},
    )
    assert response.status_code == 409
    assert client.post(
        "/api/v1/admin/offline/packages/prepare",
        json={"region_id": "", "language_id": "lang-vi"},
    ).status_code == 422


def test_rebuild_preview_does_not_publish(setup):
    client, _, service, _ = setup
    response = client.post(
        "/api/v1/admin/offline/packages/pack-1/rebuild/preview",
        json={"published_manifest": '{"sample":"data"}'},
    )
    assert response.status_code == 200, response.text
    assert response.json()["needs_rebuild"] is False
    assert response.json()["proposed_manifest"] is None
    assert service.publish_verified_rebuild.call_count == 0
    service.plan_rebuild.assert_called_once_with(
        package_id="pack-1", published_manifest=b'{"sample":"data"}',
    )


def test_admin_permission_denied(setup):
    client, app, _, _ = setup
    app.dependency_overrides[get_authentication_service] = lambda: SimpleNamespace(
        has_permission=lambda *_args, **_kwargs: False,
    )
    denied = client.get("/api/v1/admin/offline/packages")
    assert denied.status_code == 403
    assert client.post(
        "/api/v1/admin/offline/packages/prepare",
        json={"region_id": "region-1", "language_id": "lang-vi"},
    ).status_code == 403
    # Public endpoints remain accessible regardless of admin permission.
    assert client.get("/api/v1/offline/packages").status_code == 200
