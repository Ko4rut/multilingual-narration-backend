"""Persistence for logical offline packages; services own transactions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.offline.models.offline_package import OfflinePackage, OfflinePackageStatus


class OfflinePackageRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, package_id: str, *, for_update: bool = False) -> OfflinePackage | None:
        statement = select(OfflinePackage).where(OfflinePackage.id == package_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_by_key(self, package_key: str, *, for_update: bool = False) -> OfflinePackage | None:
        statement = select(OfflinePackage).where(OfflinePackage.package_key == package_key)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_published(
        self, *, region_id: str | None = None, language_id: str | None = None,
        category_id: str | None = None, offset: int = 0, limit: int = 20,
    ) -> list[OfflinePackage]:
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid package pagination")
        stmt = select(OfflinePackage).where(
            OfflinePackage.package_status == OfflinePackageStatus.PUBLISHED,
            OfflinePackage.package_url.is_not(None),
            OfflinePackage.package_checksum_sha256.is_not(None),
        )
        if region_id is not None:
            stmt = stmt.where(OfflinePackage.region_id == region_id)
        if language_id is not None:
            stmt = stmt.where(OfflinePackage.language_id == language_id)
        if category_id is not None:
            stmt = stmt.where(OfflinePackage.category_id == category_id)
        return list(self.session.scalars(
            stmt.order_by(OfflinePackage.package_key, OfflinePackage.id)
                .offset(offset).limit(limit)
        ))

    def add(self, package: OfflinePackage) -> None:
        self.session.add(package)

    def list_all(self, *, offset: int = 0, limit: int = 20) -> list[OfflinePackage]:
        """Admin-only listing; authorization happens at the HTTP boundary."""
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid package pagination")
        return list(self.session.scalars(
            select(OfflinePackage)
            .order_by(OfflinePackage.package_key, OfflinePackage.id)
            .offset(offset).limit(limit)
        ))
