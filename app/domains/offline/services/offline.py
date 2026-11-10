"""Offline-package staging and guarded rebuild publication service."""

from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import token_hex
from hashlib import sha256
from typing import Callable
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.catalog.models.region import Region
from app.domains.offline.models.offline_package import OfflinePackage, OfflinePackageStatus
from app.domains.offline.models.offline_package_item import OfflinePackageItem
from app.domains.offline.repositories.offline_package import OfflinePackageRepository
from app.domains.offline.repositories.offline_package_item import OfflinePackageItemRepository
from app.domains.offline.schemas.offline_package import OfflinePackagePage
from app.domains.offline.storage.manifest import FileSystemManifestStorage
from app.domains.offline.utils.offline import make_package_key
from app.domains.offline.utils.manifest import manifest_bytes
from app.domains.offline.utils.manifest_diff import (
    AssetDownload, ManifestChanges, compare_manifests, load_manifest,
    manifest_assets, validate_published_manifest,
)


class OfflinePackagePreparationError(ValueError):
    """Filters are unknown, unsupported or already staged/published."""


@dataclass(frozen=True)
class OfflineRebuildPlan:
    """A read-only proposed next snapshot: nothing was published or overwritten."""
    package_id: str
    expected_version: int
    expected_checksum: str
    manifest: bytes | None
    changes: ManifestChanges

    @property
    def needs_rebuild(self) -> bool:
        return self.changes.changed


class OfflinePackageNotFound(LookupError):
    """The requested offline package is not visible or does not exist."""


class OfflinePackageService:
    def __init__(
        self, session: Session, packages: OfflinePackageRepository,
        items: OfflinePackageItemRepository,
        manifest_storage: FileSystemManifestStorage | None = None,
    ):
        self.session = session
        self.packages = packages
        self.items = items
        self.manifest_storage = manifest_storage

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
            # Stage before committing the package. A filesystem failure rolls
            # back the DB transaction; a failed DB commit may leave a private
            # orphan manifest that can be cleaned up later.
            if self.manifest_storage is not None:
                self.manifest_storage.save_staged(package.id, package.package_version, manifest)
        return package, manifest

    def plan_rebuild(
        self, *, package_id: str, published_manifest: bytes,
    ) -> OfflineRebuildPlan:
        """Compare an immutable published snapshot to the current database.

        Does not mutate package or items. Callers must fetch manifest bytes from
        trusted storage using package_url; checking the stored SHA-256 prevents
        a changed/forged baseline. generated_at/version are intentionally
        excluded from change detection. Asset URLs are not fetched here.
        """
        with self.session.begin():
            package = self.packages.get_by_id(package_id)
            if package is None or package.package_status is not OfflinePackageStatus.PUBLISHED:
                raise OfflinePackagePreparationError("Only published packages can be compared")
            if not package.package_url or not package.package_checksum_sha256:
                raise OfflinePackagePreparationError("Published package lacks manifest metadata")
            region = self.session.get(Region, package.region_id)
            language = self.session.get(Language, package.language_id)
            category = self.session.get(PoiCategory, package.category_id) if package.category_id else None
            if region is None or language is None or (package.category_id and category is None):
                raise OfflinePackagePreparationError("Package has invalid filter references")
            if language.language_status is not LanguageStatus.SUPPORTED:
                raise OfflinePackagePreparationError("Language must be SUPPORTED")

            old_manifest = validate_published_manifest(
                published_manifest,
                expected_checksum=package.package_checksum_sha256,
                expected_key=package.package_key,
                expected_version=package.package_version,
                expected_schema_version=package.schema_version,
            )
            candidates = self.items.select_candidates(
                region_id=package.region_id,
                language_id=package.language_id,
                category_id=package.category_id,
            )
            # Empty results are valid for a rebuild: deleting/deactivating
            # the last POI must cause a removal, not preserve stale content.
            new_bytes = manifest_bytes(
                package_key=package.package_key,
                package_version=package.package_version + 1,
                region_code=region.region_code,
                language_code=language.language_code,
                category_code=category.category_code if category else None,
                candidates=candidates,
                generated_at=datetime.now(timezone.utc),
            )
            changes = compare_manifests(old_manifest, load_manifest(new_bytes))
            return OfflineRebuildPlan(
                package_id=package.id,
                expected_version=package.package_version,
                expected_checksum=package.package_checksum_sha256,
                manifest=new_bytes if changes.changed else None,
                changes=changes,
            )

    def publish_verified_rebuild(
        self, *, plan: OfflineRebuildPlan, published_manifest: bytes,
        manifest_url: str,
        verify_manifest: Callable[[str, bytes], bool],
        verify_asset: Callable[[AssetDownload], bool],
    ) -> OfflinePackage:
        """Replace the package snapshot only after externally verified uploads.

        Verification callbacks are trusted storage integration code, not user
        input. verify_manifest MUST fetch immutable URL bytes and compare with
        plan.manifest. verify_asset MUST verify resource bytes/checksum and
        accessibility. They run outside the database transaction to avoid
        holding row locks during network calls. This method does not upload
        files or schedule itself automatically.
        """
        if not plan.needs_rebuild or plan.manifest is None:
            raise OfflinePackagePreparationError("No changes to publish")
        parsed = load_manifest(plan.manifest)
        if (
            parsed["package_version"] != plan.expected_version + 1
            or parsed["package_key"] == ""
        ):
            raise OfflinePackagePreparationError("Invalid rebuild plan version/key")
        url = urlsplit(manifest_url)
        if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
            raise OfflinePackagePreparationError("Manifest URL must be a public HTTP(S) URL")
        # Verify all referenced assets, not only new ones. A previously known
        # checksum does not prove the remote URL is still reachable.
        for asset in manifest_assets(parsed):
            if asset.sha256 is None or len(asset.sha256) != 64:
                raise OfflinePackagePreparationError("All released assets need SHA-256")
            if not verify_asset(asset):
                raise OfflinePackagePreparationError(f"Asset verification failed: {asset.kind}")
        if not verify_manifest(manifest_url, plan.manifest):
            raise OfflinePackagePreparationError("Uploaded manifest verification failed")

        with self.session.begin():
            package = self.packages.get_by_id(plan.package_id, for_update=True)
            if (
                package is None
                or package.package_status is not OfflinePackageStatus.PUBLISHED
                or package.package_version != plan.expected_version
                or package.package_checksum_sha256 != plan.expected_checksum
            ):
                raise OfflinePackagePreparationError("Package changed since the rebuild plan")
            baseline = validate_published_manifest(
                published_manifest,
                expected_checksum=package.package_checksum_sha256,
                expected_key=package.package_key,
                expected_version=package.package_version,
                expected_schema_version=package.schema_version,
            )
            region = self.session.get(Region, package.region_id)
            language = self.session.get(Language, package.language_id)
            category = self.session.get(PoiCategory, package.category_id) if package.category_id else None
            if region is None or language is None or (package.category_id and category is None):
                raise OfflinePackagePreparationError("Invalid package filter")
            if language.language_status is not LanguageStatus.SUPPORTED:
                raise OfflinePackagePreparationError("Language must be SUPPORTED")
            candidates = self.items.select_candidates(
                region_id=package.region_id, language_id=package.language_id,
                category_id=package.category_id,
            )
            # The payload may have become stale during upload: reconstruct it
            # using the original generation timestamp and compare byte for byte.
            timestamp = datetime.fromisoformat(parsed["generated_at"].replace("Z", "+00:00"))
            latest = manifest_bytes(
                package_key=package.package_key, package_version=package.package_version + 1,
                region_code=region.region_code, language_code=language.language_code,
                category_code=category.category_code if category else None,
                candidates=candidates, generated_at=timestamp,
            )
            if latest != plan.manifest:
                raise OfflinePackagePreparationError("Source data changed; prepare a fresh rebuild")
            refreshed_changes = compare_manifests(baseline, load_manifest(latest))
            if not refreshed_changes.changed:
                raise OfflinePackagePreparationError("No content changes to publish")
            now = datetime.now(timezone.utc)
            self.items.sync_membership(
                package_id=package.id, candidates=candidates, updated_at=now,
            )
            package.package_version += 1
            package.package_url = manifest_url
            package.package_checksum_sha256 = sha256(plan.manifest).hexdigest()
            package.package_status = OfflinePackageStatus.PUBLISHED
            package.last_updated_at = now
            package.published_at = now
            # Source schema has no image byte size, so exact total is unknown.
            package.total_size = None
            self.session.flush()
        return package

    def list_published_packages(
        self, *, region_id: str | None = None, language_id: str | None = None,
        category_id: str | None = None, offset: int = 0, limit: int = 20,
    ) -> OfflinePackagePage:
        """Public mobile catalog: only packages with published manifests."""
        filters = {
            "published_only": True,
            "region_id": region_id,
            "language_id": language_id,
            "category_id": category_id,
        }
        items = self.packages.get_all(offset=offset, limit=limit, **filters)
        total = self.packages.get_count(**filters)
        return OfflinePackagePage(
            items=items, total=total, offset=offset, limit=limit,
        )

    def get_published_package(self, package_id: str) -> OfflinePackage:
        package = self.packages.get_by_id(package_id)
        if (
            package is None
            or package.package_status is not OfflinePackageStatus.PUBLISHED
            or not package.package_url
            or not package.package_checksum_sha256
        ):
            raise OfflinePackageNotFound("Offline package not found")
        return package

    def list_admin_packages(self, *, offset: int = 0, limit: int = 20) -> OfflinePackagePage:
        items = self.packages.get_all(offset=offset, limit=limit)
        total = self.packages.get_count()
        return OfflinePackagePage(
            items=items, total=total, offset=offset, limit=limit,
        )

    def get_admin_package(self, package_id: str) -> OfflinePackage:
        package = self.packages.get_by_id(package_id)
        if package is None:
            raise OfflinePackageNotFound("Offline package not found")
        return package

    def get_admin_package_items(self, package_id: str) -> list[OfflinePackageItem]:
        self.get_admin_package(package_id)
        return self.items.list_by_package(package_id)
