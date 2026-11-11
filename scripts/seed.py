from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy import Enum as SqlEnum, inspect, select, text
from sqlalchemy.orm import Session

from app.db import session_scope
from app.domains.catalog.models.language import LanguageStatus
from app.domains.identity.security.argon2_password_hasher import Argon2PasswordHasher
from app.models import (
    Action,
    Language,
    ManagementFunction,
    ManagerUser,
    Permission,
    PoiCategory,
    PoiCategoryMapping,
    PoiContent,
    PointOfInterest,
    Region,
    Role,
    RolePermission,
)


SEED_TIME = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
# Development bootstrap only. Override through SEED_ADMIN_PASSWORD outside local dev.
DEFAULT_DEV_ADMIN_PASSWORD = "admin123"

STRING_ID_PREFIXES = {
    Action: "acts",
    Language: "lang",
    ManagementFunction: "func",
    Permission: "perm",
    PoiCategory: "cat",
    Region: "region",
    Role: "role",
}
DATED_ID_PREFIXES = {
    ManagerUser: "user",
    PoiContent: "cont",
    PointOfInterest: "poi",
}


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def stable_suffix(model: type[Any], lookup: dict[str, Any], length: int = 8) -> str:
    natural_key = "|".join(
        f"{key}={lookup[key]}" for key in sorted(lookup)
    )
    return digest(f"{model.__tablename__}:{natural_key}")[:length]


def seed_id(
    model: type[Any],
    lookup: dict[str, Any],
    values: dict[str, Any],
) -> str:
    suffix = stable_suffix(model, lookup)
    if model in STRING_ID_PREFIXES:
        return f"{STRING_ID_PREFIXES[model]}-{suffix}"

    created_at = values.get("created_at", SEED_TIME)
    date_part = created_at.strftime("%d%m%y")
    if model in DATED_ID_PREFIXES:
        return f"{DATED_ID_PREFIXES[model]}-{date_part}-{suffix}"
    raise ValueError(f"No seed ID strategy for {model.__name__}")


def get_or_create(
    session: Session,
    model: type[Any],
    lookup: dict[str, Any],
    values: dict[str, Any] | None = None,
):
    instance = session.scalar(select(model).filter_by(**lookup))
    if instance is None:
        create_values = dict(values or {})
        if hasattr(model, "id") and "id" not in lookup and "id" not in create_values:
            create_values["id"] = seed_id(model, lookup, create_values)
        instance = model(**lookup, **create_values)
        session.add(instance)
        session.flush()
    return instance


def seed_identity(session: Session):
    actions = {
        name: get_or_create(session, Action, {"name": name})
        for name in ("create", "read", "update", "delete", "approve", "publish")
    }
    function_specs = [
        ("POI Management", "Manage points of interest and their metadata."),
        (
            "Narration Content Management",
            "Manage multilingual narration content and generated audio.",
        ),
        ("User Management", "Manage administrator accounts and access."),
        (
            "Offline Package Management",
            "Build and publish downloadable offline content packages.",
        ),
        ("Listening Analytics", "Review listening activity and analytics."),
        ("Language Management", "Manage the supported language catalog."),
    ]
    functions = {
        name: get_or_create(
            session, ManagementFunction, {"name": name}, {"description": description}
        )
        for name, description in function_specs
    }

    # Grant everything only when the role is first created. Re-seeding must
    # not undo permissions changed later through the administration UI.
    role_name = "Super Administrator"
    role = session.scalar(select(Role).filter_by(name=role_name))
    role_is_new = role is None
    if role_is_new:
        role = get_or_create(
            session,
            Role,
            {"name": role_name},
            {
                "description": "Full administrative access.",
                "created_at": SEED_TIME,
                "last_updated_at": SEED_TIME,
            },
        )

    permission_matrix = {
        "POI Management": ["create", "read", "update", "delete"],
        "Narration Content Management": [
            "create", "read", "update", "approve", "publish",
        ],
        "User Management": ["create", "read", "update", "delete"],
        "Offline Package Management": [
            "create", "read", "update", "delete", "publish",
        ],
        "Listening Analytics": ["read"],
        "Language Management": ["read", "create", "update"],
    }
    permissions = {}
    for function_name, action_names in permission_matrix.items():
        for action_name in action_names:
            permissions[(function_name, action_name)] = get_or_create(
                session,
                Permission,
                {
                    "function_id": functions[function_name].id,
                    "action_id": actions[action_name].id,
                },
            )

    if role_is_new:
        for permission in permissions.values():
            get_or_create(
                session,
                RolePermission,
                {"role_id": role.id, "permission_id": permission.id},
            )

    admin_email = "admin@mnr.com"
    admin = session.scalar(select(ManagerUser).filter_by(email=admin_email))
    if admin is None:
        # Hash with the same Argon2id helper used by the manager-user API.
        # The seed never stores plaintext or resets an existing admin password.
        password_hash = Argon2PasswordHasher().hash_password(
            os.environ.get("SEED_ADMIN_PASSWORD", DEFAULT_DEV_ADMIN_PASSWORD)
        )
        admin = get_or_create(
            session,
            ManagerUser,
            {"email": admin_email},
            {
                "role_id": role.id,
                "password_hash": password_hash,
                "full_name": "Quản trị hệ thống",
                "user_status": "ACTIVE",
                "created_at": SEED_TIME,
                "last_updated_at": SEED_TIME,
                "last_login_at": None,
            },
        )

    if role_is_new:
        role.created_by = admin.id
        role.last_updated_by = admin.id

    return {admin_email: admin}


def reconcile_legacy_language_statuses(session: Session) -> int:
    """Explicit, pre-0005 migration repair for legacy language VARCHAR statuses.

    Only known values are mapped: active/supported -> SUPPORTED and
    unsupported -> UNSUPPORTED (case and surrounding whitespace ignored).
    Unknown statuses are rejected rather than guessed. This uses Core SQL
    because ORM Enum loading rejects old values such as 'active'.
    Run via --reconcile-language-statuses BEFORE Alembic upgrade.
    """
    # Compose runs this before Alembic even on a completely empty volume.
    # A missing table is expected until migration 0001 has created it.
    inspector = inspect(session.connection())
    if not inspector.has_table("language"):
        return 0

    # Migrations >=0005 already use the PostgreSQL enum. No legacy VARCHAR
    # status can remain there; skip SQL designed for the pre-0005 schema.
    status_column = next(
        column for column in inspector.get_columns("language")
        if column["name"] == "language_status"
    )
    if isinstance(status_column["type"], SqlEnum):
        return 0

    statuses = session.execute(
        text("SELECT DISTINCT language_status FROM language")
    ).scalars().all()
    allowed = {"active", "supported", "unsupported"}
    unknown = [
        value for value in statuses
        if value is None or value.strip().lower() not in allowed
    ]
    if unknown:
        raise ValueError(
            "Unknown language_status values: "
            + ", ".join(repr(value) for value in unknown)
            + ". Review these rows before retrying."
        )
    result = session.execute(
        text(
            """
            UPDATE language
            SET language_status = CASE
                WHEN lower(trim(language_status)) IN ('active', 'supported')
                    THEN 'SUPPORTED'
                ELSE 'UNSUPPORTED'
            END
            WHERE language_status <> CASE
                WHEN lower(trim(language_status)) IN ('active', 'supported')
                    THEN 'SUPPORTED'
                ELSE 'UNSUPPORTED'
            END
            """
        )
    )
    return result.rowcount


def seed_catalog(session: Session):
    # Use the canonical LanguageStatus enum; avoid legacy "active" statuses.
    # Existing supported/unsupported values are intentionally not overwritten:
    # an administrator may have disabled a language after the initial seed.
    language_specs = [
        ("vi", "Tiếng Việt", LanguageStatus.SUPPORTED),
        ("en", "English", LanguageStatus.SUPPORTED),
        ("ja", "日本語", LanguageStatus.SUPPORTED),
        ("fr", "Français", LanguageStatus.SUPPORTED),
        ("ko", "한국어", LanguageStatus.SUPPORTED),
    ]
    languages = {
        code: get_or_create(
            session,
            Language,
            {"language_code": code},
            {"language_name": name, "language_status": status},
        )
        for code, name, status in language_specs
    }

    region_specs = [
        ("HAN", "Hà Nội"),
        ("NBI", "Ninh Bình"),
        ("HUE", "Thừa Thiên Huế"),
        ("DAD", "Đà Nẵng"),
        ("HCM", "Thành phố Hồ Chí Minh"),
        ("CTO", "Cần Thơ"),
    ]
    regions = {
        code: get_or_create(
            session,
            Region,
            {"region_code": code},
            {"region_name": name},
        )
        for code, name in region_specs
    }

    category_specs = [
        ("HISTORICAL", "Di tích lịch sử"),
        ("MUSEUM", "Bảo tàng"),
        ("LANDMARK", "Danh thắng"),
        ("CULTURAL", "Văn hóa"),
        ("NATURE", "Thiên nhiên"),
        ("RELIGIOUS", "Tôn giáo"),
    ]
    categories = {
        code: get_or_create(
            session,
            PoiCategory,
            {"category_code": code},
            {"category_name": name},
        )
        for code, name in category_specs
    }
    return languages, regions, categories


def seed_pois(session: Session, users, regions, categories):
    admin = users["admin@mnr.com"]
    # Three distinct regions and category combinations for development.
    poi_specs = [
        (
            "HAN-VAN-MIEU",
            "Văn Miếu - Quốc Tử Giám",
            "HAN",
            "58 Quốc Tử Giám, Đống Đa, Hà Nội",
            "21.029369",
            "105.835432",
            "80.00",
            ["HISTORICAL", "CULTURAL"],
        ),
        (
            "NBI-TRANG-AN",
            "Quần thể danh thắng Tràng An",
            "NBI",
            "Tràng An, Hoa Lư, Ninh Bình",
            "20.250864",
            "105.911184",
            "150.00",
            ["NATURE", "CULTURAL"],
        ),
        (
            "HCM-WAR-MUSEUM",
            "Bảo tàng Chứng tích Chiến tranh",
            "HCM",
            "28 Võ Văn Tần, Quận 3, Thành phố Hồ Chí Minh",
            "10.779796",
            "106.692243",
            "75.00",
            ["MUSEUM", "HISTORICAL"],
        ),
    ]

    pois = {}
    for (
        code, name, region_code, location, latitude, longitude, radius, category_codes,
    ) in poi_specs:
        # Images are placeholders; no image file or checksum is seeded.
        image_url = f"https://cdn.example.local/pois/{code.lower()}.webp"
        poi = get_or_create(
            session,
            PointOfInterest,
            {"poi_qr_code": code},
            {
                "region_id": regions[region_code].id,
                "poi_image_url": image_url,
                "image_checksum_sha256": None,
                "poi_name": name,
                "poi_location": location,
                "poi_status": "INACTIVE",
                "latitude": Decimal(latitude),
                "longitude": Decimal(longitude),
                "trigger_radius_meter": Decimal(radius),
                "created_by": admin.id,
                "last_updated_by": admin.id,
                "created_at": SEED_TIME,
                "last_updated_at": SEED_TIME,
            },
        )
        pois[code] = poi
        for category_code in category_codes:
            get_or_create(
                session,
                PoiCategoryMapping,
                {
                    "poi_id": poi.id,
                    "poi_category_id": categories[category_code].id,
                },
            )
    return pois


def seed_content(session: Session, users, languages, pois):
    admin = users["admin@mnr.com"]
    templates = {
        "vi": (
            "Khám phá {name}",
            "{name} là một điểm đến tiêu biểu tại {location}. "
            "Bản thuyết minh mẫu này cung cấp thông tin khái quát để kiểm thử "
            "trải nghiệm nghe tại điểm.",
        ),
        "en": (
            "Discover {name}",
            "{name} is a representative destination at {location}. "
            "This sample narration provides an overview for testing the "
            "on-site listening experience.",
        ),
        "ja": (
            "{name}を巡る",
            "{name}は{location}にある代表的な観光地です。このサンプル音声は現地での再生体験を確認するための概要です。",
        ),
        "fr": (
            "Découvrir {name}",
            "{name} est un site représentatif situé à {location}. "
            "Cette narration fournit un aperçu destiné aux tests de "
            "l'expérience audio sur place.",
        ),
        "ko": (
            "{name} 둘러보기",
            "{name}은(는) {location}에 있는 대표적인 명소입니다. 이 샘플 해설은 현장 오디오 경험을 테스트하기 위한 개요입니다.",
        ),
    }

    # Exactly one DRAFT content per POI/language; no audio or fake publish data.
    for index, poi in enumerate(pois.values()):
        for language_code, language in languages.items():
            title_template, script_template = templates[language_code]
            get_or_create(
                session,
                PoiContent,
                {
                    "poi_id": poi.id,
                    "language_id": language.id,
                    "content_version": 1,
                },
                {
                    "narration_title": title_template.format(name=poi.poi_name),
                    "narration_script": script_template.format(
                        name=poi.poi_name, location=poi.poi_location
                    ),
                    "content_status": "DRAFT",
                    "created_by": admin.id,
                    "approved_by": None,
                    "published_by": None,
                    "created_at": SEED_TIME + timedelta(days=index),
                    "approved_at": None,
                    "published_at": None,
                },
            )


def run_seed() -> None:
    with session_scope() as session:
        users = seed_identity(session)
        languages, regions, categories = seed_catalog(session)
        pois = seed_pois(session, users, regions, categories)
        seed_content(session, users, languages, pois)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed example narration data")
    parser.add_argument(
        "--reconcile-language-statuses",
        action="store_true",
        help="Convert known legacy language statuses before Alembic 0005; do not seed",
    )
    args = parser.parse_args()
    if args.reconcile_language_statuses:
        with session_scope() as session:
            updated = reconcile_legacy_language_statuses(session)
        print(f"Normalized {updated} legacy language rows.")
    else:
        run_seed()
        print("Seed completed successfully.")
