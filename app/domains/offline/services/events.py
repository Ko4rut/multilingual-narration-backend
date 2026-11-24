"""Transactional outbox helper used by the POI domain.

Adding the request to the SAME Session as the POI change makes the event
visible only after the source transaction commits. A rollback removes both.
"""

from datetime import datetime, timezone
from secrets import token_hex

from sqlalchemy.orm import Session

from app.domains.offline.models.build_request import OfflineBuildRequest


def enqueue_offline_build(
    session: Session, *, region_id: str, language_id: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    # Collapse repeated notifications for the exact scope in one transaction.
    for item in session.new:
        if (
            isinstance(item, OfflineBuildRequest)
            and item.region_id == region_id
            and item.language_id == language_id
            and item.status == "PENDING"
        ):
            return
    session.add(OfflineBuildRequest(
        id=f"offline-job-{token_hex(12)}",
        region_id=region_id, language_id=language_id,
        status="PENDING", attempts=0, next_attempt_at=now,
        claimed_at=None, last_error=None, created_at=now,
    ))
