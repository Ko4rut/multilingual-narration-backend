"""Automatic offline build orchestration; never invoked by Mobile or Admin.

The worker calls process_scope after the source transaction commits. All
queries and publications use fresh Sessions, never the originating POI Session.
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domains.catalog.models.language import Language, LanguageStatus
from app.domains.catalog.models.poi_category import PoiCategory
from app.domains.catalog.models.region import Region
from app.domains.offline.models.offline_package import OfflinePackage, OfflinePackageStatus
from app.domains.offline.repositories.offline_package import OfflinePackageRepository
from app.domains.offline.repositories.offline_package_item import OfflinePackageItemRepository
from app.domains.offline.services.assets import OfflineAssetVerifier
from app.domains.offline.services.offline import (
    OfflinePackagePreparationError, OfflinePackageService,
)
from app.domains.offline.storage.manifest import FileSystemManifestStorage
from app.domains.offline.utils.manifest import manifest_bytes
from app.domains.offline.utils.manifest_diff import load_manifest, manifest_assets
from app.domains.offline.utils.offline import make_package_key


class OfflinePackageBuildService:
    """Reconcile region/language packages; skip unchanged published snapshots."""

    def __init__(
        self, session_factory: Callable[[], Session],
        manifest_storage: FileSystemManifestStorage,
        settings: Settings,
        asset_verifier: OfflineAssetVerifier | None = None,
    ):
        self.session_factory = session_factory
        self.manifest_storage = manifest_storage
        self.settings = settings
        self.assets = asset_verifier or OfflineAssetVerifier(settings)

    def _service(self, session: Session) -> OfflinePackageService:
        return OfflinePackageService(
            session=session,
            packages=OfflinePackageRepository(session),
            items=OfflinePackageItemRepository(session),
            manifest_storage=self.manifest_storage,
        )

    def process_scope(self, *, region_id: str, language_id: str | None = None) -> None:
        """A region event reconciles all supported languages and existing categories.

        Automatically create the base Region+Language package when eligible.
        Category-specific packages are rebuilt if they already exist; creating
        every category combination is intentionally deferred until product scope
        has been decided.
        """
        scopes: set[tuple[str, str | None]] = set()
        with self.session_factory() as session:
            with session.begin():
                languages = session.scalars(
                    select(Language).where(Language.language_status == LanguageStatus.SUPPORTED)
                    .where(Language.id == language_id if language_id is not None else True)
                ).all()
                for language in languages:
                    existing = session.scalars(
                        select(OfflinePackage).where(
                            OfflinePackage.region_id == region_id,
                            OfflinePackage.language_id == language.id,
                        )
                    ).all()
                    candidates = OfflinePackageItemRepository(session).select_candidates(
                        region_id=region_id, language_id=language.id,
                    )
                    if candidates or any(p.category_id is None for p in existing):
                        scopes.add((language.id, None))
                    scopes.update((language.id, p.category_id) for p in existing if p.category_id)
        for lang_id, category_id in sorted(scopes, key=lambda item: (item[0], item[1] or "")):
            self.build_package(
                region_id=region_id, language_id=lang_id, category_id=category_id,
            )

    def build_package(
        self, *, region_id: str, language_id: str, category_id: str | None = None,
    ) -> bool:
        """Return True if a new manifest version was published, False if unchanged."""
        with self.session_factory() as session:
            with session.begin():
                region = session.get(Region, region_id)
                language = session.get(Language, language_id)
                category = session.get(PoiCategory, category_id) if category_id else None
                if region is None or language is None or (category_id and category is None):
                    # A source region/category may have been removed after a queued event.
                    return False
                if language.language_status is not LanguageStatus.SUPPORTED:
                    return False
                key = make_package_key(
                    region_code=region.region_code,
                    language_code=language.language_code,
                    category_code=category.category_code if category else None,
                )
                package = OfflinePackageRepository(session).get_by_key(key)
                candidates = OfflinePackageItemRepository(session).select_candidates(
                    region_id=region_id, language_id=language_id, category_id=category_id,
                )
                has_candidates = bool(candidates)
                if package is not None and package.package_status in (
                    OfflinePackageStatus.BUILDING, OfflinePackageStatus.FAILED,
                ) and has_candidates:
                    manifest = manifest_bytes(
                        package_key=key, package_version=1,
                        region_code=region.region_code, language_code=language.language_code,
                        category_code=category.category_code if category else None,
                        candidates=candidates, generated_at=datetime.now(timezone.utc),
                    )
                else:
                    manifest = None
                snapshot = (
                    (package.id, package.package_version, package.package_status,
                     package.package_checksum_sha256)
                    if package is not None else None
                )
        if snapshot is None and not has_candidates:
            return False

        package_id: str | None = snapshot[0] if snapshot else None
        initial = snapshot is None or snapshot[2] in (
            OfflinePackageStatus.BUILDING, OfflinePackageStatus.FAILED,
        )
        try:
            if snapshot is None:
                with self.session_factory() as session:
                    package, manifest = self._service(session).prepare_initial_package(
                        region_id=region_id, language_id=language_id, category_id=category_id,
                    )
                    package_id = package.id
            elif snapshot[2] is OfflinePackageStatus.PUBLISHED:
                package_id, version, _, checksum = snapshot
                if checksum is None:
                    raise OfflinePackagePreparationError("Published manifest checksum missing")
                baseline = self.manifest_storage.read_published(package_id, version, checksum)
                with self.session_factory() as session:
                    plan = self._service(session).plan_rebuild(
                        package_id=package_id, published_manifest=baseline,
                    )
                if not plan.needs_rebuild:
                    return False
                manifest = plan.manifest
            elif not has_candidates:
                return False

            if manifest is None or package_id is None:
                raise OfflinePackagePreparationError("Build did not produce a manifest")
            parsed = load_manifest(manifest)
            for asset in manifest_assets(parsed):
                if not self.assets.verify(asset):
                    raise OfflinePackagePreparationError(
                        f"Offline asset not available or checksum mismatch: {asset.kind}"
                    )
            version = parsed["package_version"]
            saved = self.manifest_storage.save_published(package_id, version, manifest)
            manifest_url = (
                self.settings.offline_manifest_public_base_url.rstrip("/")
                + f"/{package_id}/v{version}/{saved.sha256}.json"
            )

            def verify_manifest(url: str, expected: bytes) -> bool:
                return url == manifest_url and (
                    self.manifest_storage.read_published(package_id, version, saved.sha256)
                    == expected
                )

            with self.session_factory() as session:
                service = self._service(session)
                if initial:
                    service.publish_initial_package(
                        package_id=package_id, manifest=manifest,
                        manifest_url=manifest_url,
                        verify_manifest=verify_manifest, verify_asset=self.assets.verify,
                    )
                else:
                    service.publish_verified_rebuild(
                        plan=plan, published_manifest=baseline,
                        manifest_url=manifest_url, verify_manifest=verify_manifest,
                        verify_asset=self.assets.verify,
                    )
            return True
        except Exception:
            if initial and package_id is not None:
                with self.session_factory() as session:
                    self._service(session).mark_initial_failed(package_id)
            raise
