"""Listening HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.domains.listening.exceptions import (
    InvalidListeningEvent,
    ListeningEventConflict,
    ListeningReferenceNotFound,
)
from app.domains.listening.repositories.listening_history import (
    ListeningHistoryRepository,
)
from app.domains.listening.schemas.listening_history import (
    ListeningEventAck,
    ListeningEventCreate,
    ListeningDashboardSummary,
    QrScanAck,
    QrScanCreate,
)
from app.domains.listening.services.listening import ListeningService
from app.domains.identity.routers.dependencies import require_listening_analytics_read
from app.domains.identity.services.authentication import AuthenticatedIdentity
from app.route.dependencies import get_session

router = APIRouter(prefix="/listening", tags=["Listening History (Public)"])


def get_listening_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> ListeningService:
    return ListeningService(session, ListeningHistoryRepository(session))


@router.get("/dashboard", response_model=ListeningDashboardSummary)
def get_listening_dashboard(
    _identity: DashboardAccess,
    service: Annotated[ListeningService, Depends(get_listening_service)],
) -> ListeningDashboardSummary:
    return service.get_dashboard_summary()


@router.post("/events", response_model=ListeningEventAck)
def save_listening_event(
    payload: ListeningEventCreate,
    service: Annotated[ListeningService, Depends(get_listening_service)],
) -> ListeningEventAck:
    try:
        return service.save_event(payload)
    except ListeningReferenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ListeningEventConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidListeningEvent as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/qr-scans", response_model=QrScanAck)
def save_qr_scan(
    payload: QrScanCreate,
    service: Annotated[ListeningService, Depends(get_listening_service)],
) -> QrScanAck:
    """Persist one idempotent QR-triggered listening event for dashboard analytics."""
    try:
        return service.save_qr_scan(payload)
    except ListeningReferenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ListeningEventConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidListeningEvent as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
