from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.listening.exceptions import (
    InvalidListeningEvent,
    ListeningEventConflict,
    ListeningReferenceNotFound,
)
from app.domains.listening.models.listening_history import ListeningHistory
from app.domains.listening.repositories.listening_history import (
    ListeningHistoryRepository,
)
from app.domains.listening.schemas.listening_history import (
    ListeningEventAck,
    ListeningEventCreate,
    ListeningDashboardSummary,
    ListeningSaveResult,
    ListeningTriggerType,
    QrScanAck,
    QrScanCreate,
)


class ListeningService:
    def __init__(
        self,
        session: Session,
        repository: ListeningHistoryRepository,
    ):
        self.session = session
        self.repository = repository

    def get_dashboard_summary(self) -> ListeningDashboardSummary:
        return ListeningDashboardSummary(
            total_listening_sessions=self.repository.count_all()
        )

    def save_event(self, payload: ListeningEventCreate) -> ListeningEventAck:
        try:
            result = self._save_in_transaction(payload)
        except IntegrityError as exc:
            result = self._handle_integrity_error(payload, exc)
        return ListeningEventAck(id=payload.id, result=result)

    def save_qr_scan(self, payload: QrScanCreate) -> QrScanAck:
        event_payload: ListeningEventCreate | None = None
        try:
            with self.session.begin():
                poi = self.repository.get_active_poi_by_qr_code(payload.qr_code)
                if poi is None:
                    raise ListeningReferenceNotFound("Active POI for QR code not found")
                event_payload = ListeningEventCreate(
                    id=payload.id,
                    installation_id=payload.installation_id,
                    poi_id=poi.id,
                    poi_content_id=payload.poi_content_id,
                    trigger_type=ListeningTriggerType.QR_CODE,
                    started_at=payload.scanned_at,
                )
                result = self._save_in_current_transaction(event_payload)
        except IntegrityError as exc:
            if event_payload is None:
                raise
            result = self._handle_integrity_error(event_payload, exc)

        return QrScanAck(
            id=payload.id,
            result=result,
            poi_id=event_payload.poi_id,
            poi_content_id=event_payload.poi_content_id,
        )

    def _save_in_transaction(
        self, payload: ListeningEventCreate
    ) -> ListeningSaveResult:
        with self.session.begin():
            return self._save_in_current_transaction(payload)

    def _save_in_current_transaction(
        self, payload: ListeningEventCreate
    ) -> ListeningSaveResult:
        event = self.repository.get_by_id(payload.id, for_update=True)
        if event is not None:
            result = self._reconcile(event, payload)
            self.session.flush()
            return result

        self._require_valid_references(payload)
        event = ListeningHistory(
            id=payload.id,
            installation_id=payload.installation_id,
            poi_id=payload.poi_id,
            poi_content_id=payload.poi_content_id,
            trigger_type=payload.trigger_type.value,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
            duration_sec=payload.duration_sec,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.add(event)
        self.session.flush()
        return ListeningSaveResult.CREATED

    def _handle_integrity_error(
        self,
        payload: ListeningEventCreate,
        exc: IntegrityError,
    ) -> ListeningSaveResult:
        constraint = self._constraint_name(exc)
        if constraint == "listening_history_pkey":
            return self._reconcile_after_insert_race(payload)
        if constraint == "listening_history_poi_id_fkey":
            raise ListeningReferenceNotFound("POI not found") from exc
        if constraint == "listening_history_poi_content_id_fkey":
            raise ListeningReferenceNotFound("POI content not found") from exc
        raise exc

    def _reconcile_after_insert_race(
        self, payload: ListeningEventCreate
    ) -> ListeningSaveResult:
        with self.session.begin():
            event = self.repository.get_by_id(payload.id, for_update=True)
            if event is None:
                raise RuntimeError(
                    "Listening event disappeared after primary-key conflict"
                )
            result = self._reconcile(event, payload)
            self.session.flush()
            return result

    def _require_valid_references(self, payload: ListeningEventCreate) -> None:
        if not self.repository.poi_exists(payload.poi_id):
            raise ListeningReferenceNotFound("POI not found")
        content = self.repository.get_content(payload.poi_content_id)
        if content is None:
            raise ListeningReferenceNotFound("POI content not found")
        if content.poi_id != payload.poi_id:
            raise InvalidListeningEvent("POI content does not belong to the POI")

    def _reconcile(
        self,
        event: ListeningHistory,
        payload: ListeningEventCreate,
    ) -> ListeningSaveResult:
        immutable_values = (
            (event.installation_id, payload.installation_id),
            (event.poi_id, payload.poi_id),
            (event.poi_content_id, payload.poi_content_id),
            (event.trigger_type, payload.trigger_type.value),
            (self._as_utc(event.started_at), payload.started_at),
        )
        if any(stored != incoming for stored, incoming in immutable_values):
            raise ListeningEventConflict(
                "Listening event ID already exists with different identifying data"
            )

        changed = False
        if payload.duration_sec is not None and (
            event.duration_sec is None or payload.duration_sec > event.duration_sec
        ):
            event.duration_sec = payload.duration_sec
            changed = True
        if payload.completed_at is not None and (
            event.completed_at is None
            or payload.completed_at > self._as_utc(event.completed_at)
        ):
            event.completed_at = payload.completed_at
            changed = True
        if changed:
            return ListeningSaveResult.UPDATED
        return ListeningSaveResult.UNCHANGED

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
