from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.domains.catalog.exceptions import (
    LanguageAlreadyExists,
    LanguageInUse,
    LanguageNotFound,
)
from app.domains.catalog.models import LanguageStatus
from app.domains.catalog.services import CatalogService


class SessionStub:
    def begin(self):
        return nullcontext()

    def flush(self):
        pass


class RepositoryStub:
    def __init__(self):
        self.record = None
        self.conflict = None
        self.referenced = False
        self.added = None
        self.deleted = None

    def get_by_id(self, language_id):
        return self.record

    def find_conflict(self, **kwargs):
        return self.conflict

    def is_referenced(self, language_id):
        return self.referenced

    def add(self, record):
        self.added = record

    def delete(self, record):
        self.deleted = record


def build_service(repository):
    return CatalogService(
        session=SessionStub(),
        language_repository=repository,
        region_repository=SimpleNamespace(),
        poi_category_repository=SimpleNamespace(),
        id_factory=lambda prefix: f"{prefix}-12345678",
    )


def test_create_language_generates_documented_identifier():
    repository = RepositoryStub()
    language = build_service(repository).create_language(
        language_code="en",
        language_name="English",
        language_status=LanguageStatus.SUPPORTED,
    )
    assert language.id == "lang-12345678"
    assert repository.added is language


def test_create_language_rejects_code_or_name_conflict():
    repository = RepositoryStub()
    repository.conflict = object()
    with pytest.raises(LanguageAlreadyExists):
        build_service(repository).create_language(
            language_code="en",
            language_name="English",
            language_status=LanguageStatus.SUPPORTED,
        )


def test_update_missing_language_is_not_found():
    with pytest.raises(LanguageNotFound):
        build_service(RepositoryStub()).update_language(
            "lang-missing", language_name="New name"
        )


def test_delete_referenced_language_is_conflict_and_not_deleted():
    repository = RepositoryStub()
    repository.record = SimpleNamespace(id="lang-12345678")
    repository.referenced = True
    with pytest.raises(LanguageInUse):
        build_service(repository).delete_language("lang-12345678")
    assert repository.deleted is None
