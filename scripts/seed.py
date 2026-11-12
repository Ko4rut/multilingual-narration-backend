from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy import Enum as SqlEnum, delete, inspect, select, text
from sqlalchemy.orm import Session

from app.db import session_scope
from app.core.config import get_settings
from app.domains.catalog.models.language import LanguageStatus
from app.domains.identity.security.argon2_password_hasher import Argon2PasswordHasher
from app.domains.poi.providers.qr_code import create_poi_qr_payload
from app.models import (
    Action,
    Language,
    ManagementFunction,
    ManagerUser,
    OfflinePackage,
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
        ("district-1", "District 1"),
        ("district-3", "District 3"),
        ("district-4", "District 4"),
        ("district-5", "District 5"),
        ("district-6", "District 6"),
        ("district-7", "District 7"),
        ("district-8", "District 8"),
        ("district-10", "District 10"),
        ("district-11", "District 11"),
        ("district-12", "District 12"),
        ("binh-tan-district", "Binh Tan District"),
        ("binh-thanh-district", "Binh Thanh District"),
        ("go-vap-district", "Go Vap District"),
        ("phu-nhuan-district", "Phu Nhuan District"),
        ("tan-binh-district", "Tan Binh District"),
        ("tan-phu-district", "Tan Phu District"),
    ]
    regions = {}
    for code, name in region_specs:
        region = get_or_create(
            session,
            Region,
            {"region_code": code},
            {"region_name": name},
        )
        # Catalog seed labels are canonical English demo data.
        region.region_name = name
        regions[code] = region

    category_specs = [
        ("HISTORICAL", "Historical Site"),
        ("MUSEUM", "Museum"),
        ("MARKET", "Market"),
        ("ARCHITECTURE", "Architecture"),
        ("CULTURAL", "Cultural Site"),
        ("RELIGIOUS", "Religious Site"),
    ]
    categories = {}
    for code, name in category_specs:
        category = get_or_create(
            session,
            PoiCategory,
            {"category_code": code},
            {"category_name": name},
        )
        category.category_name = name
        categories[code] = category
    return languages, regions, categories


def seed_pois(session: Session, users, regions, categories):
    admin = users["admin@mnr.com"]
    image_base_url = get_settings().poi_image_public_base_url.rstrip("/")
    poi_specs = [
        (
            "ben-thanh-market",
            "Ben Thanh Market",
            "district-1",
            "Le Loi Street, Ben Thanh Ward, District 1, Ho Chi Minh City",
            "10.772461",
            "106.698055",
            "60.00",
            ["MARKET", "CULTURAL"],
            "8b44c8c70e5656f16af3f293b5c9c3e6818261958cc697ec25e21cceebcd3121.jpg",
        ),
        (
            "saigon-central-post-office",
            "Saigon Central Post Office",
            "district-1",
            "2 Cong Xa Paris Square, Ben Nghe Ward, District 1, Ho Chi Minh City",
            "10.779725",
            "106.699939",
            "50.00",
            ["ARCHITECTURE", "HISTORICAL"],
            "fdd96e601f5817e677df800b3057219dc1b8639d08a138bb966413ced1e92c3b.jpg",
        ),
        (
            "war-remnants-museum",
            "War Remnants Museum",
            "district-3",
            "28 Vo Van Tan Street, Vo Thi Sau Ward, District 3, Ho Chi Minh City",
            "10.779796",
            "106.692243",
            "75.00",
            ["MUSEUM", "HISTORICAL"],
            "c3f5f7632a5412accbbe0c1a220d710d1731712bc35021d6caaedcdecea6257c.jpg",
        ),
    ]

    pois = {}
    for (
        code, name, region_code, location, latitude, longitude, radius,
        category_codes, image_filename,
    ) in poi_specs:
        poi_id = seed_id(
            PointOfInterest,
            {"seed_key": code},
            {"created_at": SEED_TIME},
        )
        image_checksum = image_filename.split(".", 1)[0]
        poi = get_or_create(
            session,
            PointOfInterest,
            {"id": poi_id},
            {
                "region_id": regions[region_code].id,
                "poi_image_url": f"{image_base_url}/{image_filename}",
                "image_checksum_sha256": image_checksum,
                "poi_qr_code": create_poi_qr_payload(poi_id),
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
        poi.region_id = regions[region_code].id
        poi.poi_image_url = f"{image_base_url}/{image_filename}"
        poi.image_checksum_sha256 = image_checksum
        poi.poi_qr_code = create_poi_qr_payload(poi.id)
        poi.poi_name = name
        poi.poi_location = location
        poi.poi_status = "INACTIVE"
        poi.latitude = Decimal(latitude)
        poi.longitude = Decimal(longitude)
        poi.trigger_radius_meter = Decimal(radius)
        poi.last_updated_by = admin.id
        poi.last_updated_at = SEED_TIME
        session.execute(
            delete(PoiCategoryMapping).where(PoiCategoryMapping.poi_id == poi.id)
        )
        session.flush()
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
    content_specs = {
        "ben-thanh-market": {
            "en": (
                "Welcome to Ben Thanh Market",
                "Ben Thanh Market is one of Ho Chi Minh City's best-known landmarks. "
                "Opened in 1914, it remains a lively destination for local food, "
                "handicrafts, textiles, and everyday commerce.",
            ),
            "vi": (
                "Chào mừng đến Chợ Bến Thành",
                "Chợ Bến Thành là một trong những biểu tượng nổi tiếng của Thành phố "
                "Hồ Chí Minh. Hoạt động từ năm 1914, chợ là điểm đến sôi động với ẩm "
                "thực địa phương, hàng thủ công, vải vóc và nhiều mặt hàng thiết yếu.",
            ),
            "ja": (
                "ベンタイン市場へようこそ",
                "ベンタイン市場はホーチミン市を代表する名所の一つです。1914年に開業し、"
                "地元の料理や工芸品、織物、日用品が並ぶ活気ある市場として親しまれています。",
            ),
            "fr": (
                "Bienvenue au marché Ben Thanh",
                "Le marché Ben Thanh est l'un des monuments les plus connus de Hô Chi "
                "Minh-Ville. Ouvert en 1914, il reste un lieu animé pour la cuisine "
                "locale, l'artisanat, les textiles et le commerce quotidien.",
            ),
            "ko": (
                "벤탄 시장에 오신 것을 환영합니다",
                "벤탄 시장은 호찌민시를 대표하는 명소 중 하나입니다. 1914년에 문을 연 뒤 "
                "현지 음식과 수공예품, 직물, 생활용품을 만날 수 있는 활기찬 시장으로 사랑받고 있습니다.",
            ),
        },
        "saigon-central-post-office": {
            "en": (
                "Discover Saigon Central Post Office",
                "Saigon Central Post Office was built between 1886 and 1891. Its "
                "arched hall, iron structure, historic maps, and yellow facade make "
                "it a distinctive landmark that still operates as a post office.",
            ),
            "vi": (
                "Khám phá Bưu điện Trung tâm Sài Gòn",
                "Bưu điện Trung tâm Sài Gòn được xây dựng từ năm 1886 đến 1891. Mái "
                "vòm, kết cấu sắt, các bản đồ cổ và mặt tiền màu vàng tạo nên một công "
                "trình đặc trưng vẫn đang phục vụ người dân đến ngày nay.",
            ),
            "ja": (
                "サイゴン中央郵便局を訪ねて",
                "サイゴン中央郵便局は1886年から1891年にかけて建設されました。アーチ状の"
                "ホール、鉄骨構造、歴史的な地図、黄色い外壁が特徴で、現在も郵便局として営業しています。",
            ),
            "fr": (
                "Découvrez la Poste centrale de Saïgon",
                "La Poste centrale de Saïgon a été construite entre 1886 et 1891. Sa "
                "halle voûtée, sa structure métallique, ses cartes anciennes et sa "
                "façade jaune en font un monument qui fonctionne toujours comme poste.",
            ),
            "ko": (
                "사이공 중앙우체국 둘러보기",
                "사이공 중앙우체국은 1886년부터 1891년 사이에 건축되었습니다. 아치형 홀과 "
                "철골 구조, 옛 지도, 노란 외관이 특징이며 지금도 우체국으로 운영되고 있습니다.",
            ),
        },
        "war-remnants-museum": {
            "en": (
                "Visit the War Remnants Museum",
                "The War Remnants Museum presents photographs, documents, military "
                "equipment, and personal accounts related to the wars in Vietnam. It "
                "invites visitors to reflect on the human impact of war and peace.",
            ),
            "vi": (
                "Tham quan Bảo tàng Chứng tích Chiến tranh",
                "Bảo tàng Chứng tích Chiến tranh trưng bày hình ảnh, tài liệu, phương "
                "tiện quân sự và những câu chuyện cá nhân liên quan đến các cuộc chiến "
                "tại Việt Nam, giúp khách tham quan suy ngẫm về chiến tranh và hòa bình.",
            ),
            "ja": (
                "戦争証跡博物館を訪ねて",
                "戦争証跡博物館では、ベトナムでの戦争に関する写真、資料、軍用装備、"
                "個人の証言を展示し、戦争が人々に与えた影響と平和について考える機会を提供しています。",
            ),
            "fr": (
                "Visitez le musée des Vestiges de la guerre",
                "Le musée présente des photographies, des documents, du matériel "
                "militaire et des témoignages liés aux guerres au Vietnam. Il invite "
                "les visiteurs à réfléchir aux conséquences humaines de la guerre.",
            ),
            "ko": (
                "전쟁박물관 방문",
                "전쟁박물관은 베트남 전쟁과 관련된 사진, 문서, 군사 장비와 개인의 증언을 "
                "전시하며 전쟁이 사람들에게 남긴 영향과 평화의 의미를 생각하게 합니다.",
            ),
        },
    }

    # Mỗi POI có một bản nháp version 1 cho mọi ngôn ngữ được hỗ trợ.
    for poi_index, (seed_key, poi) in enumerate(pois.items()):
        for language_index, (language_code, (title, script)) in enumerate(
            content_specs[seed_key].items()
        ):
            language = languages[language_code]
            content = get_or_create(
                session,
                PoiContent,
                {
                    "poi_id": poi.id,
                    "language_id": language.id,
                    "content_version": 1,
                },
                {
                    "narration_title": title,
                    "narration_script": script,
                    "content_status": "DRAFT",
                    "created_by": admin.id,
                    "approved_by": None,
                    "published_by": None,
                    "created_at": SEED_TIME + timedelta(
                        days=poi_index, minutes=language_index
                    ),
                    "approved_at": None,
                    "published_at": None,
                },
            )
            # Không ghi đè nội dung đã đi vào workflow hoặc đã được xuất bản.
            if content.content_status == "DRAFT":
                content.narration_title = title
                content.narration_script = script


def remove_unreferenced_legacy_catalog(session: Session) -> None:
    """Xóa catalog demo cũ chỉ khi không còn bản ghi nghiệp vụ tham chiếu."""
    for code in ("HAN", "NBI", "HUE", "DAD", "HCM", "CTO"):
        region = session.scalar(select(Region).where(Region.region_code == code))
        if region is None:
            continue
        has_poi = session.scalar(
            select(PointOfInterest.id).where(PointOfInterest.region_id == region.id).limit(1)
        )
        has_package = session.scalar(
            select(OfflinePackage.id).where(OfflinePackage.region_id == region.id).limit(1)
        )
        if has_poi is None and has_package is None:
            session.delete(region)
    for code in ("LANDMARK", "NATURE"):
        category = session.scalar(
            select(PoiCategory).where(PoiCategory.category_code == code)
        )
        if category is None:
            continue
        has_mapping = session.scalar(
            select(PoiCategoryMapping.poi_id)
            .where(PoiCategoryMapping.poi_category_id == category.id)
            .limit(1)
        )
        has_package = session.scalar(
            select(OfflinePackage.id)
            .where(OfflinePackage.category_id == category.id)
            .limit(1)
        )
        if has_mapping is None and has_package is None:
            session.delete(category)


def run_seed() -> None:
    with session_scope() as session:
        users = seed_identity(session)
        languages, regions, categories = seed_catalog(session)
        pois = seed_pois(session, users, regions, categories)
        seed_content(session, users, languages, pois)
        remove_unreferenced_legacy_catalog(session)


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
