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
)
from app.domains.listening.services.listening import ListeningService
from app.route.dependencies import get_session

router = APIRouter(prefix="/listening", tags=["listening"])


def get_listening_service(
    session: Annotated[Session, Depends(get_session, use_cache=False)],
) -> ListeningService:
    return ListeningService(session, ListeningHistoryRepository(session))


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
