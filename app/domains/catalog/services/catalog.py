from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.catalog.exceptions import (
    LanguageAlreadyExists, LanguageNotFound, PoiCategoryAlreadyExists,
    PoiCategoryInUse, PoiCategoryNotFound,
)
from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.catalog.models.region import Region
from app.domains.catalog.repositories.language import LanguageRepository
from app.domains.catalog.repositories.poi_category import PoiCategoryRepository
from app.domains.catalog.repositories.region import RegionRepository
from app.domains.catalog.utils import generate_catalog_identifier, get_constraint_name


class CatalogService:
    def __init__(
        self,
        session: Session,
        language_repository: LanguageRepository,
        region_repository: RegionRepository,
        category_repository: PoiCategoryRepository,
        *,
        id_factory: Callable[[str], str] = generate_catalog_identifier,
    ):
        self.session = session
        self.language_repository = language_repository
        self.region_repository = region_repository
        self.category_repository = category_repository
        self.id_factory = id_factory

    def list_regions(self) -> list[Region]:
        return self.region_repository.get_all()

    def list_categories(self) -> list[PoiCategory]:
        return self.category_repository.get_all()

    def _require_category(self, category_id: str, *, for_update: bool = False) -> PoiCategory:
        category = self.category_repository.get_by_id(category_id, for_update=for_update)
        if category is None:
            raise PoiCategoryNotFound("POI Category not found")
        return category

    def _require_available_category(
        self, *, category_name: str | None = None,
        category_code: str | None = None, exclude_id: str | None = None,
    ) -> None:
        if self.category_repository.get_conflict(
            category_name=category_name, category_code=category_code,
            exclude_id=exclude_id,
        ) is not None:
            raise PoiCategoryAlreadyExists("POI Category name or code already exists")

    def create_category(self, *, category_name: str, category_code: str) -> PoiCategory:
        try:
            with self.session.begin():
                self._require_available_category(
                    category_name=category_name, category_code=category_code,
                )
                category = PoiCategory(
                    id=self.id_factory("cat"),
                    category_name=category_name,
                    category_code=category_code,
                )
                self.category_repository.add(category)
                self.session.flush()
        except IntegrityError as exc:
            self._translate_category_integrity_error(exc)
        return category

    def update_category(self, category_id: str, *, category_name: str) -> PoiCategory:
        """Only the name is mutable: category_code participates in package_key."""
        try:
            with self.session.begin():
                category = self._require_category(category_id, for_update=True)
                if category.category_name != category_name:
                    self._require_available_category(
                        category_name=category_name, exclude_id=category_id,
                    )
                    category.category_name = category_name
                    self.session.flush()
        except IntegrityError as exc:
            self._translate_category_integrity_error(exc)
        return category

    def delete_category(self, category_id: str) -> None:
        """Delete only an unreferenced Category, under a locked transaction."""
        try:
            with self.session.begin():
                category = self._require_category(category_id, for_update=True)
                if self.category_repository.is_referenced(category_id):
                    raise PoiCategoryInUse(
                        "POI Category is referenced by POIs or offline packages"
                    )
                self.category_repository.delete(category)
                self.session.flush()
        except IntegrityError as exc:
            self._translate_category_integrity_error(exc)

    @staticmethod
    def _translate_category_integrity_error(exc: IntegrityError) -> None:
        name = get_constraint_name(exc)
        if name in {
            "uq_poi_category_name", "poi_category_category_code_key",
        }:
            raise PoiCategoryAlreadyExists(
                "POI Category name or code already exists"
            ) from exc
        if name in {
            "poi_category_mapping_poi_category_id_fkey",
            "offline_package_category_id_fkey",
        }:
            raise PoiCategoryInUse(
                "POI Category is referenced by POIs or offline packages"
            ) from exc
        raise exc

    def list_supported_languages(self) -> list[Language]:
        return self.language_repository.get_supported()

    def list_languages(self) -> list[Language]:
        return self.language_repository.get_all()

    def create_language(
        self, *, language_code: str, language_name: str, language_status: LanguageStatus
    ) -> Language:
        try:
            with self.session.begin():
                self._require_available_language(
                    language_code=language_code, language_name=language_name
                )
                language = Language(
                    id=self.id_factory("lang"),
                    language_code=language_code,
                    language_name=language_name,
                    language_status=language_status,
                )
                self.language_repository.add(language)
                self.session.flush()
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return language

    def _require_language(self, language_id: str) -> Language:
        language = self.language_repository.get_by_id(language_id)
        if language is None:
            raise LanguageNotFound("Language not found")
        return language

    def update_language(
        self,
        language_id: str,
        *,
        language_name: str | None = None,
        language_status: LanguageStatus | None = None,
    ) -> Language:
        try:
            with self.session.begin():
                language = self._require_language(language_id)
                if language_name is not None and language_name != language.language_name:
                    self._require_available_language(
                        language_name=language_name, exclude_id=language_id
                    )
                    language.language_name = language_name
                if language_status is not None:
                    language.language_status = language_status
                self.session.flush()
        except IntegrityError as exc:
            self._translate_integrity_error(exc)
        return language

    def _require_available_language(
        self,
        *,
        language_code: str | None = None,
        language_name: str | None = None,
        exclude_id: str | None = None,
    ) -> None:
        if self.language_repository.get_conflict(
            language_code=language_code,
            language_name=language_name,
            exclude_id=exclude_id,
        ) is not None:
            raise LanguageAlreadyExists("Language code or name already exists")

    def _translate_integrity_error(self, exc: IntegrityError) -> None:
        constraint = get_constraint_name(exc)
        if constraint in {"language_language_code_key", "language_language_name_key"}:
            raise LanguageAlreadyExists("Language code or name already exists") from exc
        raise exc
