import re

import pytest

from app.models import (
    Action,
    ContentAudio,
    Language,
    ListeningHistory,
    ManagementFunction,
    ManagerUser,
    OfflinePackage,
    OfflinePackageItem,
    Permission,
    PoiCategory,
    PoiContent,
    PointOfInterest,
    Region,
    Role,
    UserSession,
)
from scripts.seed import SEED_TIME, seed_id


@pytest.mark.parametrize(
    ("model", "prefix"),
    [
        (ManagerUser, "user"),
        (PointOfInterest, "poi"),
        (PoiContent, "cont"),
        (ContentAudio, "audio"),
        (OfflinePackage, "pack"),
        (OfflinePackageItem, "pack-item"),
        (UserSession, "sess"),
        (ListeningHistory, "listen"),
    ],
)
def test_dated_varchar_ids_have_eight_character_suffix(model, prefix):
    identifier = seed_id(
        model,
        {"natural_key": model.__tablename__},
        {"created_at": SEED_TIME},
    )

    assert isinstance(identifier, str)
    assert re.fullmatch(rf"{prefix}-010926-[0-9a-f]{{8}}", identifier)


@pytest.mark.parametrize(
    ("model", "prefix"),
    [
        (Action, "acts"),
        (ManagementFunction, "func"),
        (Permission, "perm"),
        (Role, "role"),
        (PoiCategory, "cat"),
        (Region, "region"),
        (Language, "lang"),
    ],
)
def test_reference_ids_have_eight_character_suffix(model, prefix):
    identifier = seed_id(
        model,
        {"natural_key": model.__tablename__},
        {},
    )

    assert re.fullmatch(rf"{prefix}-[0-9a-f]{{8}}", identifier)
