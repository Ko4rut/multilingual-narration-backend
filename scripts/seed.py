from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select

from app.db import session_scope
from app.models import (
    Action, AuditLog, ContentAudio, Language, ListeningHistory, ManagementFunction,
    ManagementUser, OfflinePackage, Permission, PoiCategory, PoiCategoryMapping,
    PoiContent, PointOfInterest, Region, Role, RolePermission,
)

NOW = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)


def get_or_create(session, model, lookup: dict, values: dict | None = None):
    obj = session.scalar(select(model).filter_by(**lookup))
    if obj is None:
        obj = model(**lookup, **(values or {}))
        session.add(obj)
        session.flush()
    return obj


def run_seed() -> None:
    with session_scope() as session:
        actions = {name: get_or_create(session, Action, {"name": name}) for name in ["create", "read", "update", "delete", "publish", "generate_audio"]}
        functions = {name: get_or_create(session, ManagementFunction, {"name": name}) for name in ["POI Management", "Narration Content Management", "User Management", "Offline Package Management"]}
        roles = {name: get_or_create(session, Role, {"name": name}) for name in ["System Administrator", "Content Administrator"]}
        perms = {}
        for fn_name, action_names in {
            "POI Management": ["create", "read", "update", "delete"],
            "Narration Content Management": ["create", "read", "update", "delete", "publish", "generate_audio"],
            "User Management": ["create", "read", "update", "delete"],
            "Offline Package Management": ["create", "read", "update", "delete"],
        }.items():
            for action_name in action_names:
                key = (fn_name, action_name)
                perms[key] = get_or_create(session, Permission, {"function_id": functions[fn_name].id, "action_id": actions[action_name].id})
        admin_all = list(perms.values())
        content_allowed = [perms[(fn, act)] for fn, acts in [("POI Management", ["create", "read", "update", "delete"]), ("Narration Content Management", ["create", "read", "update", "delete", "publish", "generate_audio"]), ("Offline Package Management", ["create", "read", "update"])] for act in acts]
        for permission in admin_all:
            get_or_create(session, RolePermission, {"role_id": roles["System Administrator"].id, "permission_id": permission.id})
        for permission in content_allowed:
            get_or_create(session, RolePermission, {"role_id": roles["Content Administrator"].id, "permission_id": permission.id})

        users = {}
        users["admin"] = get_or_create(session, ManagementUser, {"email_address": "admin@narration.local"}, {
            "password_hash": "$2b$12$DEVELOPMENT_ONLY_DUMMY_HASH_REPLACE_IN_REAL_ENVIRONMENT",
            "role_id": roles["System Administrator"].id, "full_name": "System Administrator", "gender": "unspecified",
            "date_of_birth": date(1985, 5, 12), "created_at": NOW, "is_delete": False,
        })
        users["content"] = get_or_create(session, ManagementUser, {"email_address": "content.admin@narration.local"}, {
            "password_hash": "$2b$12$DEVELOPMENT_ONLY_DUMMY_HASH_REPLACE_IN_REAL_ENVIRONMENT",
            "role_id": roles["Content Administrator"].id, "full_name": "Content Administrator", "gender": "unspecified",
            "date_of_birth": date(1990, 8, 20), "created_at": NOW, "is_delete": False,
        })

        languages = {}
        for code, name in [("vi", "Vietnamese"), ("en", "English"), ("ja", "Japanese")]:
            languages[code] = get_or_create(session, Language, {"language_code": code}, {"language_name": name, "is_active": True})
        regions = {name: get_or_create(session, Region, {"name": name}) for name in ["Hanoi Old Quarter", "Hue Imperial City", "Ho Chi Minh City"]}
        categories = {name: get_or_create(session, PoiCategory, {"name": name}) for name in ["Historical Site", "Museum", "Landmark", "Cultural Site"]}

        poi_specs = [
            ("Temple of Literature", "Hanoi Old Quarter", "HANOI-TOL-001", 1, Decimal("21.0294"), Decimal("105.8350"), Decimal("80.00"), "58 Quoc Tu Giam, Hanoi", ["Historical Site", "Cultural Site"]),
            ("Hue Imperial City", "Hue Imperial City", "HUE-IMPERIAL-001", 1, Decimal("16.4698"), Decimal("107.5790"), Decimal("120.00"), "Phu Hau, Hue", ["Historical Site", "Landmark"]),
            ("War Remnants Museum", "Ho Chi Minh City", "HCMC-WRM-001", 2, Decimal("10.7798"), Decimal("106.6926"), Decimal("70.00"), "28 Vo Van Tan, Ho Chi Minh City", ["Museum", "Historical Site"]),
            ("Saigon Central Post Office", "Ho Chi Minh City", "HCMC-POST-001", 3, Decimal("10.7798"), Decimal("106.6990"), Decimal("65.00"), "2 Cong Xa Paris, Ho Chi Minh City", ["Landmark", "Cultural Site"]),
        ]
        pois = {}
        for name, region_name, qr, priority, lat, lon, radius, location, cat_names in poi_specs:
            poi = get_or_create(session, PointOfInterest, {"qr_code": qr}, {
                "region_id": regions[region_name].id, "image_url": f"https://example.local/images/{qr.lower()}.jpg",
                "poi_priority": priority, "poi_name": name, "latitude": lat, "longitude": lon,
                "trigger_radius": radius, "poi_location": location, "created_by": users["content"].id, "is_active": True, "created_at": NOW,
            })
            pois[name] = poi
            for cat_name in cat_names:
                get_or_create(session, PoiCategoryMapping, {"poi_id": poi.id, "poi_category_id": categories[cat_name].id})

        scripts = {
            "Temple of Literature": {
                "vi": ("Văn Miếu - Quốc Tử Giám", "Văn Miếu được xây dựng năm 1070 và là biểu tượng lâu đời của truyền thống giáo dục Việt Nam.", "https://example.local/audio/temple-vi.mp3", "tts_generated"),
                "en": ("Temple of Literature", "The Temple of Literature was founded in 1070 and represents Vietnam's long tradition of scholarship and education.", "https://example.local/audio/temple-en.mp3", "pre_generated"),
                "ja": ("文廟", "文廟は1070年に建立され、ベトナムの学問と教育の長い伝統を象徴しています。", "https://example.local/audio/temple-ja.mp3", "tts_generated"),
            },
            "Hue Imperial City": {
                "vi": ("Đại Nội Huế", "Đại Nội Huế là quần thể cung điện nằm trong Kinh thành Huế, trung tâm quyền lực của triều Nguyễn.", "https://example.local/audio/hue-vi.mp3", "pre_generated"),
                "en": ("Hue Imperial City", "Hue Imperial City is a palace complex inside the citadel and was the political center of the Nguyen dynasty.", "https://example.local/audio/hue-en.mp3", "tts_generated"),
                "ja": ("フエ王宮", "フエ王宮は城塞内にある宮殿群で、グエン朝の政治的中心地でした。", "https://example.local/audio/hue-ja.mp3", "tts_generated"),
            },
            "War Remnants Museum": {
                "vi": ("Bảo tàng Chứng tích Chiến tranh", "Bảo tàng giới thiệu các tư liệu và hiện vật lịch sử về chiến tranh tại Việt Nam.", "https://example.local/audio/wrm-vi.mp3", "pre_generated"),
                "en": ("War Remnants Museum", "The museum presents historical documents and artifacts about the wars in Vietnam.", "https://example.local/audio/wrm-en.mp3", "tts_generated"),
            },
            "Saigon Central Post Office": {
                "vi": ("Bưu điện Trung tâm Sài Gòn", "Bưu điện Trung tâm Sài Gòn là công trình kiến trúc nổi bật được xây dựng vào cuối thế kỷ XIX.", "https://example.local/audio/post-vi.mp3", "pre_generated"),
                "en": ("Saigon Central Post Office", "Saigon Central Post Office is a prominent late nineteenth-century architectural landmark.", "https://example.local/audio/post-en.mp3", "tts_generated"),
                "ja": ("サイゴン中央郵便局", "サイゴン中央郵便局は19世紀末に建設された代表的な建築ランドマークです。", "https://example.local/audio/post-ja.mp3", "tts_generated"),
            },
        }
        content_map = {}
        for poi_name, lang_specs in scripts.items():
            for code, (title, script, url, source) in lang_specs.items():
                lang = languages[code]
                content = get_or_create(session, PoiContent, {"poi_id": pois[poi_name].id, "language_id": lang.id}, {
                    "narration_title": title, "narration_script": script, "content_status": "published",
                    "created_by": users["content"].id, "published_at": NOW,
                })
                content_map[(poi_name, code)] = content
                checksum = sha256(url.encode()).hexdigest()
                get_or_create(session, ContentAudio, {"checksum_sha25": checksum}, {
                    "poi_content_id": content.id, "audio_url": url, "audio_size": 245760 + len(script) * 80,
                    "audio_source_type": source, "created_at": NOW,
                })

        history = [
            ("Temple of Literature", 75, 0),
            ("Hue Imperial City", 132, 1),
            ("War Remnants Museum", 98, 2),
        ]
        for idx, (poi_name, duration, day_offset) in enumerate(history, 1):
            started = NOW.replace(hour=9 + idx, minute=10 + idx, second=0)
            if session.scalar(select(ListeningHistory).where(ListeningHistory.poi_id == pois[poi_name].id, ListeningHistory.started_at == started)) is None:
                session.add(ListeningHistory(poi_id=pois[poi_name].id, started_at=started, completed_at=started.replace(minute=started.minute + min(59, duration // 60)), duration_sec=duration, created_at=started))

        package_specs = [
            ("Hanoi Vietnamese Heritage", "Hanoi Old Quarter", "Historical Site", "vi", 8_500_000),
            ("Hanoi English Heritage", "Hanoi Old Quarter", None, "en", 7_900_000),
            ("Hue Japanese Heritage", "Hue Imperial City", "Historical Site", "ja", 6_800_000),
            ("Ho Chi Minh Museum English", "Ho Chi Minh City", "Museum", "en", 9_200_000),
        ]
        for name, region_name, cat_name, code, size in package_specs:
            get_or_create(session, OfflinePackage, {"name": name}, {"category_id": categories[cat_name].id if cat_name else None, "region_id": regions[region_name].id, "language_id": languages[code].id, "total_size": size, "created_at": NOW})

        audit_specs = [
            (users["content"].id, "create", "Point_Of_Interest", pois["Temple of Literature"].id, None, {"poi_name": "Temple of Literature", "qr_code": "HANOI-TOL-001"}),
            (users["content"].id, "publish", "Poi_Content", content_map[("Temple of Literature", "vi")].id, {"content_status": "draft"}, {"content_status": "published"}),
            (users["admin"].id, "update", "Point_Of_Interest", pois["War Remnants Museum"].id, {"trigger_radius": 60}, {"trigger_radius": 70}),
        ]
        for user_id, action, entity_type, entity_id, old_values, new_values in audit_specs:
            exists = session.scalar(select(AuditLog).where(AuditLog.user_id == user_id, AuditLog.action == action, AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id))
            if exists is None:
                session.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, old_values=old_values, new_values=new_values, created_at=NOW))


if __name__ == "__main__":
    run_seed()
    print("Seed completed successfully.")
