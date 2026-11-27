from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.domains.catalog.exceptions import (
    PoiCategoryAlreadyExists,
    PoiCategoryInUse,
    PoiCategoryNotFound,
)
from app.domains.catalog.services import CatalogService


class SessionStub:
    def __init__(self):
        self.began = 0
        self.flushed = 0

    def begin(self):
        self.began += 1
        return nullcontext()

    def flush(self):
        self.flushed += 1


class CategoryRepositoryStub:
    def __init__(self, category=None):
        self.category = category
        self.conflict = None
        self.referenced = False
        self.added = None
        self.deleted = None
        self.locked = False

    def get_by_id(self, _id, *, for_update=False):
        self.locked = for_update
        return self.category

    def get_conflict(self, **_kwargs):
        return self.conflict

    def is_referenced(self, _id):
        return self.referenced

    def add(self, category):
        self.added = category

    def delete(self, category):
        self.deleted = category


def service_for(category_repository):
    session = SessionStub()
    service = CatalogService(
        session=session,
        category_repository=category_repository,
        language_repository=SimpleNamespace(),
        region_repository=SimpleNamespace(),
        id_factory=lambda prefix: f"{prefix}-12345678",
    )
    return service, session


def test_create_category_generates_id_and_flushes_once():
    repository = CategoryRepositoryStub()
    service, session = service_for(repository)

    category = service.create_category(
        category_name="Heritage", category_code="heritage",
    )
    assert category.id == "cat-12345678"
    assert category.category_name == "Heritage"
    assert repository.added is category
    assert session.began == 1
    assert session.flushed == 1


def test_create_category_rejects_duplicate():
    repository = CategoryRepositoryStub()
    repository.conflict = object()
    service, session = service_for(repository)
    with pytest.raises(PoiCategoryAlreadyExists):
        service.create_category(category_name="Museum", category_code="museum")
    assert session.began == 1
    assert session.flushed == 0


def test_update_category_changes_name_only_and_locks_record():
    category = SimpleNamespace(
        id="cat-1", category_name="Museum", category_code="MUSEUM",
    )
    repository = CategoryRepositoryStub(category)
    service, session = service_for(repository)
    result = service.update_category("cat-1", category_name="Art Museum")
    assert result is category
    assert category.category_name == "Art Museum"
    assert category.category_code == "MUSEUM"
    assert repository.locked
    assert session.began == 1
    assert session.flushed == 1


def test_update_category_missing_raises():
    service, _ = service_for(CategoryRepositoryStub())
    with pytest.raises(PoiCategoryNotFound):
        service.update_category("cat-missing", category_name="Museum")


def test_update_duplicate_name_is_rejected_before_mutating():
    category = SimpleNamespace(id="cat-1", category_name="Museum", category_code="MUSEUM")
    repository = CategoryRepositoryStub(category)
    repository.conflict = object()
    service, _ = service_for(repository)
    with pytest.raises(PoiCategoryAlreadyExists):
        service.update_category("cat-1", category_name="Other")
    assert category.category_name == "Museum"


def test_delete_category_checks_both_kinds_of_references():
    category = SimpleNamespace(id="cat-1", category_name="Museum", category_code="MUSEUM")
    repository = CategoryRepositoryStub(category)
    repository.referenced = True
    service, _ = service_for(repository)
    with pytest.raises(PoiCategoryInUse):
        service.delete_category("cat-1")
    assert repository.locked
    assert repository.deleted is None


def test_delete_category_unreferenced():
    category = SimpleNamespace(id="cat-1", category_name="Museum", category_code="MUSEUM")
    repository = CategoryRepositoryStub(category)
    service, session = service_for(repository)
    service.delete_category("cat-1")
    assert repository.locked
    assert repository.deleted is category
    assert session.began == 1
    assert session.flushed == 1


def test_delete_missing_category_is_not_found():
    service, _ = service_for(CategoryRepositoryStub())
    with pytest.raises(PoiCategoryNotFound):
        service.delete_category("cat-missing")
