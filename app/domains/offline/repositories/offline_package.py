"""Persistence for logical offline packages; services own transactions."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

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

    def get_all(
        self, *, offset: int = 0, limit: int = 20,
        published_only: bool = False, region_id: str | None = None,
        language_id: str | None = None, category_id: str | None = None,
    ) -> list[OfflinePackage]:
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid package pagination")
        filters = self._get_filters(
            published_only=published_only,
            region_id=region_id,
            language_id=language_id,
            category_id=category_id,
        )
        return list(self.session.scalars(
            select(OfflinePackage).where(*filters)
                .order_by(OfflinePackage.package_key, OfflinePackage.id)
                .offset(offset).limit(limit)
        ))

    def get_count(
        self, *, published_only: bool = False,
        region_id: str | None = None, language_id: str | None = None,
        category_id: str | None = None,
    ) -> int:
        """Đếm package theo cùng bộ lọc của ``get_all``."""
        filters = self._get_filters(
            published_only=published_only,
            region_id=region_id,
            language_id=language_id,
            category_id=category_id,
        )
        return self.session.scalar(
            select(func.count()).select_from(OfflinePackage).where(*filters)
        )

    @staticmethod
    def _get_filters(
        *, published_only: bool, region_id: str | None,
        language_id: str | None, category_id: str | None,
    ) -> list[ColumnElement[bool]]:
        """Tạo bộ lọc dùng chung cho danh sách và tổng số package."""
        filters: list[ColumnElement[bool]] = []
        if published_only:
            filters.extend((
                OfflinePackage.package_status == OfflinePackageStatus.PUBLISHED,
                OfflinePackage.package_url.is_not(None),
                OfflinePackage.package_checksum_sha256.is_not(None),
            ))
        if region_id is not None:
            filters.append(OfflinePackage.region_id == region_id)
        if language_id is not None:
            filters.append(OfflinePackage.language_id == language_id)
        if category_id is not None:
            filters.append(OfflinePackage.category_id == category_id)
        return filters

    def add(self, package: OfflinePackage) -> None:
        self.session.add(package)
