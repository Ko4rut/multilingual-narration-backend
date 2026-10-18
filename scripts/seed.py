from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import (
    Action,
    AuditLog,
    ContentAudio,
    Language,
    ListeningHistory,
    ManagementFunction,
    ManagerUser,
    OfflinePackage,
    OfflinePackageItem,
    Permission,
    PoiCategory,
    PoiCategoryMapping,
    PoiContent,
    PointOfInterest,
    Region,
    Role,
    RolePermission,
    UserSession,
)


SEED_TIME = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
DUMMY_PASSWORD_HASH = (
    "$2b$12$DEVELOPMENT_ONLY_DUMMY_HASH_REPLACE_BEFORE_REAL_AUTH"
)


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def get_or_create(
    session: Session,
    model: type[Any],
    lookup: dict[str, Any],
    values: dict[str, Any] | None = None,
):
    instance = session.scalar(select(model).filter_by(**lookup))
    if instance is None:
        instance = model(**lookup, **(values or {}))
        session.add(instance)
        session.flush()
    return instance


def seed_identity(session: Session):
    actions = {
        name: get_or_create(session, Action, {"name": name})
        for name in [
            "create",
            "read",
            "update",
            "delete",
            "approve",
            "publish",
            "generate_audio",
        ]
    }
    functions = {
        name: get_or_create(session, ManagementFunction, {"name": name})
        for name in [
            "POI Management",
            "Narration Content Management",
            "User Management",
            "Offline Package Management",
            "Listening Analytics",
        ]
    }
    roles = {
        name: get_or_create(
            session,
            Role,
            {"name": name},
            {"created_at": SEED_TIME, "last_updated_at": SEED_TIME},
        )
        for name in [
            "System Administrator",
            "Content Editor",
            "Content Reviewer",
        ]
    }

    permission_matrix = {
        "POI Management": ["create", "read", "update", "delete"],
        "Narration Content Management": [
            "create",
            "read",
            "update",
            "delete",
            "approve",
            "publish",
            "generate_audio",
        ],
        "User Management": ["create", "read", "update", "delete"],
        "Offline Package Management": ["create", "read", "update", "delete", "publish"],
        "Listening Analytics": ["read"],
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

    role_grants = {
        "System Administrator": list(permissions),
        "Content Editor": [
            ("POI Management", "create"),
            ("POI Management", "read"),
            ("POI Management", "update"),
            ("Narration Content Management", "create"),
            ("Narration Content Management", "read"),
            ("Narration Content Management", "update"),
            ("Narration Content Management", "generate_audio"),
            ("Offline Package Management", "read"),
        ],
        "Content Reviewer": [
            ("POI Management", "read"),
            ("Narration Content Management", "read"),
            ("Narration Content Management", "approve"),
            ("Narration Content Management", "publish"),
            ("Offline Package Management", "read"),
            ("Offline Package Management", "publish"),
            ("Listening Analytics", "read"),
        ],
    }
    for role_name, grant_keys in role_grants.items():
        for grant_key in grant_keys:
            get_or_create(
                session,
                RolePermission,
                {
                    "permission_id": permissions[grant_key].id,
                    "role_id": roles[role_name].id,
                },
            )

    user_specs = [
        (
            "admin@mnr.local",
            "System Administrator",
            "Quản trị hệ thống",
            "active",
            SEED_TIME + timedelta(hours=1),
        ),
        (
            "editor@mnr.local",
            "Content Editor",
            "Biên tập viên nội dung",
            "active",
            SEED_TIME + timedelta(hours=2),
        ),
        (
            "reviewer@mnr.local",
            "Content Reviewer",
            "Kiểm duyệt viên nội dung",
            "active",
            SEED_TIME + timedelta(hours=3),
        ),
        (
            "archived@mnr.local",
            "Content Editor",
            "Tài khoản lưu trữ",
            "inactive",
            None,
        ),
    ]
    users = {}
    for email, role_name, full_name, status, last_login_at in user_specs:
        users[email] = get_or_create(
            session,
            ManagerUser,
            {"email": email},
            {
                "role_id": roles[role_name].id,
                "password_hash": DUMMY_PASSWORD_HASH,
                "full_name": full_name,
                "user_status": status,
                "created_at": SEED_TIME,
                "last_updated_at": SEED_TIME,
                "last_login_at": last_login_at,
            },
        )

    session_specs = [
        (
            "admin@mnr.local",
            "admin-refresh-token-example",
            SEED_TIME + timedelta(days=30),
            None,
        ),
        (
            "editor@mnr.local",
            "editor-refresh-token-example",
            SEED_TIME + timedelta(days=14),
            None,
        ),
        (
            "reviewer@mnr.local",
            "reviewer-revoked-token-example",
            SEED_TIME + timedelta(days=7),
            SEED_TIME + timedelta(days=1),
        ),
    ]
    for email, token, expires_at, revoked_at in session_specs:
        token_hash = digest(token)
        get_or_create(
            session,
            UserSession,
            {"refresh_token_hash": token_hash},
            {
                "user_id": users[email].id,
                "expires_at": expires_at,
                "created_at": SEED_TIME,
                "revoked_at": revoked_at,
            },
        )

    return users


def seed_catalog(session: Session):
    language_specs = [
        ("vi", "Tiếng Việt", "active"),
        ("en", "English", "active"),
        ("ja", "日本語", "active"),
        ("fr", "Français", "active"),
        ("ko", "한국어", "active"),
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
    editor = users["editor@mnr.local"]
    reviewer = users["reviewer@mnr.local"]
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
            "active",
        ),
        (
            "HAN-HO-GUOM",
            "Hồ Hoàn Kiếm",
            "HAN",
            "Phố Đinh Tiên Hoàng, Hoàn Kiếm, Hà Nội",
            "21.028779",
            "105.852448",
            "120.00",
            ["LANDMARK", "NATURE"],
            "active",
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
            "active",
        ),
        (
            "NBI-HOA-LU",
            "Cố đô Hoa Lư",
            "NBI",
            "Trường Yên, Hoa Lư, Ninh Bình",
            "20.284316",
            "105.907407",
            "100.00",
            ["HISTORICAL", "RELIGIOUS"],
            "active",
        ),
        (
            "HUE-DAI-NOI",
            "Đại Nội Huế",
            "HUE",
            "Phú Hậu, thành phố Huế",
            "16.469791",
            "107.578769",
            "140.00",
            ["HISTORICAL", "CULTURAL"],
            "active",
        ),
        (
            "HUE-THIEN-MU",
            "Chùa Thiên Mụ",
            "HUE",
            "Hương Long, thành phố Huế",
            "16.453164",
            "107.544973",
            "90.00",
            ["RELIGIOUS", "LANDMARK"],
            "active",
        ),
        (
            "DAD-CAU-RONG",
            "Cầu Rồng",
            "DAD",
            "Đường Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
            "16.061087",
            "108.227264",
            "130.00",
            ["LANDMARK"],
            "active",
        ),
        (
            "DAD-NGU-HANH-SON",
            "Danh thắng Ngũ Hành Sơn",
            "DAD",
            "81 Huyền Trân Công Chúa, Ngũ Hành Sơn, Đà Nẵng",
            "16.003591",
            "108.263535",
            "150.00",
            ["NATURE", "RELIGIOUS"],
            "active",
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
            "active",
        ),
        (
            "HCM-CENTRAL-POST",
            "Bưu điện Trung tâm Sài Gòn",
            "HCM",
            "2 Công xã Paris, Quận 1, Thành phố Hồ Chí Minh",
            "10.779950",
            "106.699934",
            "70.00",
            ["LANDMARK", "CULTURAL"],
            "active",
        ),
        (
            "CTO-CAI-RANG",
            "Chợ nổi Cái Răng",
            "CTO",
            "Sông Cần Thơ, quận Cái Răng, Cần Thơ",
            "10.003972",
            "105.748237",
            "180.00",
            ["CULTURAL", "LANDMARK"],
            "active",
        ),
        (
            "CTO-BINH-THUY",
            "Nhà cổ Bình Thủy",
            "CTO",
            "144 Bùi Hữu Nghĩa, Bình Thủy, Cần Thơ",
            "10.064577",
            "105.733285",
            "60.00",
            ["HISTORICAL", "CULTURAL"],
            "maintenance",
        ),
    ]

    pois = {}
    for (
        code,
        name,
        region_code,
        location,
        latitude,
        longitude,
        radius,
        category_codes,
        status,
    ) in poi_specs:
        image_url = f"https://cdn.example.local/pois/{code.lower()}.webp"
        poi = get_or_create(
            session,
            PointOfInterest,
            {"poi_qr_code": code},
            {
                "region_id": regions[region_code].id,
                "poi_image_url": image_url,
                "image_checksum_sha256": digest(image_url),
                "poi_name": name,
                "poi_location": location,
                "poi_status": status,
                "latitude": Decimal(latitude),
                "longitude": Decimal(longitude),
                "trigger_radius_meter": Decimal(radius),
                "created_by": editor.id,
                "last_updated_by": reviewer.id,
                "created_at": SEED_TIME,
                "last_updated_at": SEED_TIME + timedelta(days=7),
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
    editor = users["editor@mnr.local"]
    reviewer = users["reviewer@mnr.local"]
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
    extra_languages = ["ja", "fr", "ko"]
    content_map = {}
    audio_map = {}

    for index, (poi_code, poi) in enumerate(pois.items()):
        language_codes = ["vi", "en", extra_languages[index % len(extra_languages)]]
        for language_index, language_code in enumerate(language_codes):
            title_template, script_template = templates[language_code]
            title = title_template.format(name=poi.poi_name)
            script = script_template.format(
                name=poi.poi_name,
                location=poi.poi_location,
            )
            content = get_or_create(
                session,
                PoiContent,
                {
                    "poi_id": poi.id,
                    "language_id": languages[language_code].id,
                    "content_version": 1,
                },
                {
                    "narration_title": title,
                    "narration_script": script,
                    "content_status": "published",
                    "created_by": editor.id,
                    "approved_by": reviewer.id,
                    "published_by": reviewer.id,
                    "created_at": SEED_TIME + timedelta(days=index),
                    "approved_at": SEED_TIME + timedelta(days=index, hours=2),
                    "published_at": SEED_TIME + timedelta(days=index, hours=4),
                },
            )
            content_map[(poi_code, language_code, 1)] = content

            audio_url = (
                f"https://cdn.example.local/audio/{poi_code.lower()}-"
                f"{language_code}-v1.mp3"
            )
            audio = get_or_create(
                session,
                ContentAudio,
                {"audio_checksum_sha256": digest(audio_url)},
                {
                    "poi_content_id": content.id,
                    "audio_url": audio_url,
                    "audio_size": 320_000 + len(script.encode("utf-8")) * 120,
                    "audio_source_type": (
                        "pre_generated"
                        if (index + language_index) % 2 == 0
                        else "tts_generated"
                    ),
                    "audio_duration_sec": 75 + index * 4 + language_index * 6,
                    "audio_mime_type": "audio/mpeg",
                    "created_at": SEED_TIME + timedelta(days=index, hours=4),
                    "last_updated_at": SEED_TIME + timedelta(days=index, hours=4),
                },
            )
            audio_map[(poi_code, language_code, 1)] = audio

    first_poi = pois["HAN-VAN-MIEU"]
    get_or_create(
        session,
        PoiContent,
        {
            "poi_id": first_poi.id,
            "language_id": languages["vi"].id,
            "content_version": 2,
        },
        {
            "narration_title": "Văn Miếu - bản biên tập mới",
            "narration_script": (
                "Bản nháp phiên bản hai dùng để kiểm thử quy trình duyệt "
                "nội dung."
            ),
            "content_status": "draft",
            "created_by": editor.id,
            "approved_by": None,
            "published_by": None,
            "created_at": SEED_TIME + timedelta(days=20),
            "approved_at": None,
            "published_at": None,
        },
    )
    return content_map, audio_map


def seed_listening_history(session: Session, pois, content_map):
    trigger_types = ["gps", "qr_code", "manual"]
    language_codes = ["vi", "en", "ja", "fr", "ko"]
    published_entries = list(content_map.items())

    for index in range(36):
        (poi_code, language_code, _), content = published_entries[
            index % len(published_entries)
        ]
        if language_code not in language_codes:
            continue
        started_at = SEED_TIME + timedelta(days=30 + index // 6, minutes=index * 13)
        duration = 52 + (index * 11) % 130
        incomplete = index in {11, 29}
        installation_id = f"install-{(index % 9) + 1:03d}"
        existing = session.scalar(
            select(ListeningHistory).where(
                ListeningHistory.installation_id == installation_id,
                ListeningHistory.started_at == started_at,
            )
        )
        if existing is None:
            session.add(
                ListeningHistory(
                    installation_id=installation_id,
                    poi_content_id=content.id,
                    poi_id=pois[poi_code].id,
                    trigger_type=trigger_types[index % len(trigger_types)],
                    started_at=started_at,
                    completed_at=(
                        None
                        if incomplete
                        else started_at + timedelta(seconds=duration)
                    ),
                    duration_sec=None if incomplete else duration,
                    created_at=started_at,
                )
            )


def seed_offline_packages(
    session: Session,
    languages,
    regions,
    categories,
    pois,
    content_map,
    audio_map,
):
    package_specs = [
        (
            "hanoi-vi",
            "HAN",
            "vi",
            None,
            "published",
            ["HAN-VAN-MIEU", "HAN-HO-GUOM"],
        ),
        (
            "ninh-binh-en",
            "NBI",
            "en",
            "NATURE",
            "published",
            ["NBI-TRANG-AN"],
        ),
        (
            "hue-fr",
            "HUE",
            "fr",
            "HISTORICAL",
            "published",
            ["HUE-DAI-NOI"],
        ),
        (
            "da-nang-fr",
            "DAD",
            "fr",
            None,
            "published",
            ["DAD-NGU-HANH-SON"],
        ),
        (
            "ho-chi-minh-en",
            "HCM",
            "en",
            "MUSEUM",
            "published",
            ["HCM-WAR-MUSEUM"],
        ),
        (
            "can-tho-ko",
            "CTO",
            "ko",
            "CULTURAL",
            "building",
            ["CTO-BINH-THUY"],
        ),
    ]

    for index, (
        key,
        region_code,
        language_code,
        category_code,
        status,
        package_poi_codes,
    ) in enumerate(package_specs, start=1):
        item_keys = [
            (poi_code, language_code, 1) for poi_code in package_poi_codes
        ]
        total_size = sum(audio_map[item_key].audio_size for item_key in item_keys)
        package_url = f"https://cdn.example.local/packages/{key}-v1.zip"
        package = get_or_create(
            session,
            OfflinePackage,
            {"package_key": key, "package_version": 1},
            {
                "category_id": (
                    categories[category_code].id if category_code else None
                ),
                "region_id": regions[region_code].id,
                "language_id": languages[language_code].id,
                "package_name": f"Gói ngoại tuyến {key}",
                "package_url": package_url,
                "total_size": total_size,
                "package_checksum_sha256": digest(package_url),
                "package_status": status,
                "schema_version": 1,
                "created_at": SEED_TIME + timedelta(days=45 + index),
                "last_updated_at": SEED_TIME + timedelta(days=45 + index),
                "published_at": (
                    SEED_TIME + timedelta(days=45 + index, hours=2)
                    if status == "published"
                    else None
                ),
            },
        )

        for item_key in item_keys:
            poi_code, _, content_version = item_key
            content = content_map[item_key]
            audio = audio_map[item_key]
            get_or_create(
                session,
                OfflinePackageItem,
                {
                    "package_id": package.id,
                    "poi_id": pois[poi_code].id,
                    "poi_content_id": content.id,
                    "audio_id": audio.id,
                },
                {
                    "content_version": content_version,
                    "created_at": package.created_at,
                    "last_updated_at": package.last_updated_at,
                },
            )


def seed_audit_logs(session: Session, users, pois, content_map):
    editor = users["editor@mnr.local"]
    reviewer = users["reviewer@mnr.local"]
    admin = users["admin@mnr.local"]
    audit_specs = [
        (
            editor.id,
            "create",
            "point_of_interest",
            pois["HAN-VAN-MIEU"].id,
            None,
            {"poi_name": "Văn Miếu - Quốc Tử Giám", "poi_status": "active"},
        ),
        (
            reviewer.id,
            "publish",
            "poi_content",
            content_map[("HAN-VAN-MIEU", "vi", 1)].id,
            {"content_status": "approved"},
            {"content_status": "published"},
        ),
        (
            editor.id,
            "update",
            "point_of_interest",
            pois["HUE-DAI-NOI"].id,
            {"trigger_radius_meter": "120.00"},
            {"trigger_radius_meter": "140.00"},
        ),
        (
            admin.id,
            "update",
            "manager_user",
            editor.id,
            {"user_status": "pending"},
            {"user_status": "active"},
        ),
        (
            reviewer.id,
            "update",
            "point_of_interest",
            pois["CTO-BINH-THUY"].id,
            {"poi_status": "active"},
            {"poi_status": "maintenance"},
        ),
    ]
    for index, (
        user_id,
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
    ) in enumerate(audit_specs):
        existing = session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == user_id,
                AuditLog.action == action,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
        )
        if existing is None:
            session.add(
                AuditLog(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    old_values=old_values,
                    new_values=new_values,
                    created_at=SEED_TIME + timedelta(days=60, minutes=index),
                )
            )


def run_seed() -> None:
    with session_scope() as session:
        users = seed_identity(session)
        languages, regions, categories = seed_catalog(session)
        pois = seed_pois(session, users, regions, categories)
        content_map, audio_map = seed_content(
            session,
            users,
            languages,
            pois,
        )
        seed_listening_history(session, pois, content_map)
        seed_offline_packages(
            session,
            languages,
            regions,
            categories,
            pois,
            content_map,
            audio_map,
        )
        seed_audit_logs(session, users, pois, content_map)


if __name__ == "__main__":
    run_seed()
    print("Seed completed successfully.")
