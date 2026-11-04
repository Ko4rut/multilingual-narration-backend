"""Group 3 schema contract tests; no external storage or database writes."""

import app.models  # noqa: F401
import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, CheckConstraint, UniqueConstraint

from app.db import Base
from app.domains.offline.models.offline_package import OfflinePackageStatus
from app.domains.offline.schemas.offline_package import OfflinePackageRead
from app.domains.offline.utils.offline import make_package_key


def unique_columns(table):
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def check_names(table):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_offline_package_schema_matches_document():
    package = Base.metadata.tables["offline_package"]
    assert unique_columns(package) == {("package_key",)}
    assert package.c.package_url.nullable
    assert package.c.total_size.nullable
    assert isinstance(package.c.total_size.type, BigInteger)
    assert package.c.package_checksum_sha256.nullable
    assert not package.c.package_status.nullable
    assert package.c.package_status.type.name == "offline_package_status"
    assert package.c.package_status.type.enums == [
        "BUILDING", "PUBLISHED", "FAILED"
    ]
    assert {
        "ck_offline_package_version_positive",
        "ck_offline_package_schema_version_positive",
        "ck_offline_package_total_size_nonnegative",
        "ck_offline_package_published_after_creation",
    } <= check_names(package)
    assert "ix_offline_package_region_language" in {
        index.name for index in package.indexes
    }


def test_offline_item_schema_matches_document():
    item = Base.metadata.tables["offline_package_item"]
    assert unique_columns(item) == {("package_id", "poi_content_id")}
    assert "ck_offline_package_item_content_version_positive" in check_names(item)


def test_package_key_uses_canonical_catalog_codes():
    assert make_package_key(region_code="HAN", language_code="vi") == (
        "region:HAN|lang:vi"
    )
    assert make_package_key(
        region_code="HAN", language_code="vi", category_code="HISTORICAL",
    ) == "cat:HISTORICAL|region:HAN|lang:vi"
    with pytest.raises(ValueError):
        make_package_key(region_code="", language_code="vi")


def test_building_package_schema_accepts_missing_manifest():
    from datetime import datetime, timezone

    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    payload = dict(
        id="pack-test", category_id=None, region_id="region-test",
        language_id="lang-test", package_key="region:HAN|lang:vi",
        package_name="Hà Nội", package_url=None, package_version=1,
        total_size=None, package_checksum_sha256=None,
        package_status="BUILDING", schema_version=1,
        created_at=now, last_updated_at=now, published_at=None,
    )
    result = OfflinePackageRead.model_validate(payload)
    assert result.package_status is OfflinePackageStatus.BUILDING
    assert result.package_url is None
    with pytest.raises(ValidationError):
        OfflinePackageRead.model_validate({**payload, "package_status": "UNKNOWN"})
