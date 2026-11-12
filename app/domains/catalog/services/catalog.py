from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.catalog.exceptions import LanguageAlreadyExists, LanguageNotFound
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
