"""Initial offline-package staging use case (no publication or file upload)."""

from datetime import datetime, timezone
from secrets import token_hex

from sqlalchemy.orm import Session

from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.catalog.models.region import Region
from app.domains.offline.models.offline_package import OfflinePackage, OfflinePackageStatus
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.offline.repositories.offline_package import OfflinePackageRepository
from app.domains.offline.repositories.offline_package_item import OfflinePackageItemRepository
from app.domains.offline.utils.offline import make_package_key
from app.domains.offline.utils.manifest import manifest_bytes


class OfflinePackagePreparationError(ValueError):
    """Filters are unknown, unsupported or already staged/published."""


class OfflinePackageService:
    def __init__(
        self, session: Session, packages: OfflinePackageRepository,
        items: OfflinePackageItemRepository,
    ):
        self.session = session
        self.packages = packages
        self.items = items

    def prepare_initial_package(
        self, *, region_id: str, language_id: str, category_id: str | None = None,
    ) -> tuple[OfflinePackage, bytes]:
        """Persist first BUILDING package/items and return manifest bytes.

        Caller must use a new transaction and handle IntegrityError after
        rollback (concurrent creation of the same canonical package key).
        No updates to existing PUBLISHED packages are made in this phase.
        """
        with self.session.begin():
            region = self.session.get(Region, region_id)
            language = self.session.get(Language, language_id)
            category = self.session.get(PoiCategory, category_id) if category_id else None
            if region is None or language is None or (category_id and category is None):
                raise OfflinePackagePreparationError("Unknown region, language or category")
            if language.language_status is not LanguageStatus.SUPPORTED:
                raise OfflinePackagePreparationError("Language must be SUPPORTED")

            key = make_package_key(
                region_code=region.region_code,
                language_code=language.language_code,
                category_code=category.category_code if category else None,
            )
            if self.packages.get_by_key(key, for_update=True) is not None:
                raise OfflinePackagePreparationError(
                    "Package already exists; reuse the published manifest or stage a separate rebuild"
                )

            candidates = self.items.select_candidates(
                region_id=region_id, language_id=language_id, category_id=category_id,
            )
            if not candidates:
                raise OfflinePackagePreparationError("No eligible published content/audio")
            now = datetime.now(timezone.utc)
            package = OfflinePackage(
                id=f"pack-{now:%d%m%y}-{token_hex(4)}",
                category_id=category_id,
                region_id=region_id,
                language_id=language_id,
                package_key=key,
                package_name=f"{region.region_name} ({language.language_name})",
                package_url=None,
                package_version=1,
                total_size=None,  # image sizes are not stored by the current schema
                package_checksum_sha256=None,
                package_status=OfflinePackageStatus.BUILDING,
                schema_version=1,
                created_at=now,
                last_updated_at=now,
                published_at=None,
            )
            self.packages.add(package)
            self.session.flush()
            memberships = [
                OfflinePackageItem(
                    id=f"pack-item-{now:%d%m%y}-{token_hex(4)}",
                    package_id=package.id,
                    poi_id=c.poi.id,
                    poi_content_id=c.content.id,
                    audio_id=c.audio.id,
                    content_version=c.content.content_version,
                    created_at=now,
                    last_updated_at=now,
                )
                for c in candidates
            ]
            self.items.add_all(memberships)
            self.session.flush()
            manifest = manifest_bytes(
                package_key=key, package_version=1,
                region_code=region.region_code,
                language_code=language.language_code,
                category_code=category.category_code if category else None,
                candidates=candidates, generated_at=now,
            )
        return package, manifest
