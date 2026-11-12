from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.domains.catalog.exceptions import (
    LanguageAlreadyExists,
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
        self.added = None

    def get_by_id(self, language_id):
        return self.record

    def get_conflict(self, **kwargs):
        return self.conflict

    def add(self, record):
        self.added = record


def build_service(repository):
    return CatalogService(
        session=SessionStub(),
        language_repository=repository,
        region_repository=SimpleNamespace(),
        category_repository=SimpleNamespace(),
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
