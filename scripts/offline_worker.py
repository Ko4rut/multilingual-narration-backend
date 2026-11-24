"""Durable offline package worker.

Run separately from FastAPI: python -m scripts.offline_worker
Docker Compose's offline-worker service runs this automatically with the API.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 - register ORM models
from app.core.config import get_settings
from app.core.database import get_engine
from app.domains.offline.models.build_request import OfflineBuildRequest
from app.domains.offline.services.events import enqueue_offline_build
from app.domains.poi.models.point_of_interest import PointOfInterest
from app.domains.offline.services.build import OfflinePackageBuildService
from app.domains.offline.storage.manifest import FileSystemManifestStorage


logger = logging.getLogger(__name__)


def process_next(session_factory, builder: OfflinePackageBuildService) -> bool:
    """Process at most one claimed job; keep failures eligible for retry."""
    now = datetime.now(timezone.utc)
    timeout = now - timedelta(minutes=15)
    with session_factory() as session:
        with session.begin():
            job = session.scalar(
                select(OfflineBuildRequest).where(or_(
                    and_(OfflineBuildRequest.status == "PENDING",
                         OfflineBuildRequest.next_attempt_at <= now),
                    and_(OfflineBuildRequest.status == "RUNNING",
                         OfflineBuildRequest.claimed_at < timeout),
                ))
                .order_by(OfflineBuildRequest.created_at, OfflineBuildRequest.id)
                .with_for_update(skip_locked=True).limit(1)
            )
            if job is None:
                return False
            job.status = "RUNNING"
            job.attempts += 1
            job.claimed_at = now
            job_id = job.id
            attempt = job.attempts
            region_id, language_id = job.region_id, job.language_id

    error = None
    try:
        builder.process_scope(region_id=region_id, language_id=language_id)
    except Exception as exc:
        error = str(exc)
        logger.exception("Offline build failed: %s", job_id)

    with session_factory() as session:
        with session.begin():
            job = session.get(OfflineBuildRequest, job_id, with_for_update=True)
            if job is None or job.status != "RUNNING" or job.attempts != attempt:
                return True  # Another worker reclaimed the expired lease.
            job.claimed_at = None
            if error is None:
                job.status = "SUCCEEDED"
                job.last_error = None
            else:
                job.status = "PENDING"
                job.last_error = error[:1000]
                job.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=min(3600, 30 * (2 ** min(attempt - 1, 7))),
                )
    return True


def enqueue_bootstrap_regions(session_factory) -> None:
    """Reconcile ACTIVE POIs that predate deployment of the event hooks.

    Re-enqueueing an unchanged published region is harmless: manifest diff
    prevents a version bump. This also recovers a missing package for an
    already populated region after a worker restart.
    """
    with session_factory() as session:
        with session.begin():
            regions = session.scalars(
                select(PointOfInterest.region_id)
                .where(PointOfInterest.poi_status == "ACTIVE").distinct()
            ).all()
            for region_id in regions:
                pending = session.scalar(
                    select(OfflineBuildRequest.id).where(
                        OfflineBuildRequest.region_id == region_id,
                        OfflineBuildRequest.language_id.is_(None),
                        OfflineBuildRequest.status.in_(("PENDING", "RUNNING")),
                    ).limit(1)
                )
                if pending is None:
                    enqueue_offline_build(session, region_id=region_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)
    builder = OfflinePackageBuildService(
        session_factory=factory,
        manifest_storage=FileSystemManifestStorage(settings.offline_manifest_dir),
        settings=settings,
    )
    enqueue_bootstrap_regions(factory)
    logger.info("Offline auto-build worker started")
    while True:
        try:
            if not process_next(factory, builder):
                time.sleep(5)
        except Exception:
            logger.exception("Offline worker polling error")
            time.sleep(5)


if __name__ == "__main__":
    main()
