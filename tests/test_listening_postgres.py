import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from secrets import choice, token_hex
from string import ascii_lowercase
from threading import Barrier

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - register all foreign-key targets
from app.domains.catalog.models import Language, LanguageStatus, Region
from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.models.role import RoleModel
from app.domains.listening.models import ListeningHistory
from app.domains.listening.repositories import ListeningHistoryRepository
from app.domains.listening.schemas import ListeningEventCreate
from app.domains.listening.services import ListeningService
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.models.point_of_interest import PointOfInterest


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to an isolated PostgreSQL database",
)
def test_concurrent_same_id_is_idempotent_on_postgresql():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    suffix = token_hex(4)
    now = datetime.now(timezone.utc)
    role_id = f"role-listen-{suffix}"
    user_id = f"user-listen-{suffix}"
    region_id = f"region-listen-{suffix}"
    language_id = f"lang-listen-{suffix}"
    poi_id = f"poi-091126-{suffix}"
    content_id = f"cont-091126-{suffix}"
    event_id = f"listen-091126-{suffix}"
    language_code = "".join(choice(ascii_lowercase) for _ in range(3))
    barrier = Barrier(2)
    update_barrier = Barrier(2)

    class RacingRepository(ListeningHistoryRepository):
        def get_by_id(self, requested_id, *, for_update=False):
            event = super().get_by_id(requested_id, for_update=for_update)
            if event is None:
                barrier.wait(timeout=10)
            return event

    try:
        with Session(engine) as session, session.begin():
            revision = session.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision == "0008_listening_events"
            session.add_all(
                [
                    RoleModel(
                        id=role_id,
                        name=f"Listening Test Role {suffix}",
                        description=None,
                        created_by=None,
                        last_updated_by=None,
                        created_at=now,
                        last_updated_at=now,
                    ),
                    Region(
                        id=region_id,
                        region_name=f"Listening Test Region {suffix}",
                        region_code=f"listen-{suffix}",
                    ),
                    Language(
                        id=language_id,
                        language_code=language_code,
                        language_name=f"Listening Test Language {suffix}",
                        language_status=LanguageStatus.SUPPORTED,
                    ),
                ]
            )
            session.flush()
            session.add(
                ManagerUserModel(
                    id=user_id,
                    role_id=role_id,
                    email=f"listening-{suffix}@test.invalid",
                    password_hash="test-only",
                    full_name="Listening Test User",
                    user_status=ManagerUserStatus.ACTIVE,
                    created_at=now,
                    last_updated_at=now,
                    last_login_at=None,
                )
            )
            session.flush()
            session.add(
                PointOfInterest(
                    id=poi_id,
                    region_id=region_id,
                    poi_image_url=None,
                    image_checksum_sha256=None,
                    poi_qr_code=f"qr-listen-{suffix}",
                    poi_name=f"Listening Test POI {suffix}",
                    poi_location=f"Listening Test Location {suffix}",
                    poi_status="inactive",
                    latitude=Decimal("10.000000"),
                    longitude=Decimal("106.000000"),
                    trigger_radius_meter=Decimal("25.00"),
                    created_by=user_id,
                    last_updated_by=user_id,
                    created_at=now,
                    last_updated_at=now,
                )
            )
            session.flush()
            session.add(
                PoiContent(
                    id=content_id,
                    poi_id=poi_id,
                    language_id=language_id,
                    narration_title="Listening concurrency test",
                    narration_script="Test",
                    content_version=1,
                    content_status="DRAFT",
                    created_by=user_id,
                    approved_by=None,
                    published_by=None,
                    created_at=now,
                    approved_at=None,
                    published_at=None,
                )
            )

        def save(duration):
            with Session(engine) as session:
                service = ListeningService(session, RacingRepository(session))
                return service.save_event(
                    ListeningEventCreate(
                        id=event_id,
                        installation_id="c0a80121-7ac0-4f20-90a0-52df3b17e901",
                        poi_id=poi_id,
                        poi_content_id=content_id,
                        trigger_type="AUTO_LOCATION",
                        started_at=now,
                        duration_sec=duration,
                    )
                ).result.value

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(save, (10, 20)))

        with Session(engine) as session:
            rows = list(
                session.scalars(
                    select(ListeningHistory).where(ListeningHistory.id == event_id)
                )
            )
            assert len(rows) == 1
            assert rows[0].duration_sec == 20
            assert "CREATED" in results
            assert set(results) <= {"CREATED", "UPDATED", "UNCHANGED"}

        def update(duration, completed_at):
            update_barrier.wait(timeout=10)
            with Session(engine) as session:
                service = ListeningService(
                    session, ListeningHistoryRepository(session)
                )
                return service.save_event(
                    ListeningEventCreate(
                        id=event_id,
                        installation_id="c0a80121-7ac0-4f20-90a0-52df3b17e901",
                        poi_id=poi_id,
                        poi_content_id=content_id,
                        trigger_type="AUTO_LOCATION",
                        started_at=now,
                        completed_at=completed_at,
                        duration_sec=duration,
                    )
                ).result.value

        with ThreadPoolExecutor(max_workers=2) as executor:
            update_results = list(
                executor.map(
                    lambda arguments: update(*arguments),
                    (
                        (30, now + timedelta(minutes=5)),
                        (40, now + timedelta(minutes=4)),
                    ),
                )
            )

        with Session(engine) as session:
            service = ListeningService(
                session, ListeningHistoryRepository(session)
            )
            stale_result = service.save_event(
                ListeningEventCreate(
                    id=event_id,
                    installation_id="c0a80121-7ac0-4f20-90a0-52df3b17e901",
                    poi_id=poi_id,
                    poi_content_id=content_id,
                    trigger_type="AUTO_LOCATION",
                    started_at=now,
                    completed_at=now + timedelta(minutes=3),
                    duration_sec=10,
                )
            ).result.value
            event = session.get(ListeningHistory, event_id)
            assert event is not None
            assert event.duration_sec == 40
            assert event.completed_at == now + timedelta(minutes=5)
            assert set(update_results) == {"UPDATED"}
            assert stale_result == "UNCHANGED"
    finally:
        with Session(engine) as session, session.begin():
            session.execute(
                delete(ListeningHistory).where(ListeningHistory.id == event_id)
            )
            session.execute(delete(PoiContent).where(PoiContent.id == content_id))
            session.execute(
                delete(PointOfInterest).where(PointOfInterest.id == poi_id)
            )
            session.execute(
                delete(ManagerUserModel).where(ManagerUserModel.id == user_id)
            )
            session.execute(delete(RoleModel).where(RoleModel.id == role_id))
            session.execute(delete(Language).where(Language.id == language_id))
            session.execute(delete(Region).where(Region.id == region_id))
        engine.dispose()
