from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


ListeningId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=22,
        max_length=22,
        pattern=r"^listen-\d{6}-[0-9a-f]{8}$",
    ),
]
ReferenceId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
QrCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
DurationSeconds = Annotated[int, Field(strict=True, ge=0)]


class ListeningTriggerType(str, Enum):
    AUTO_LOCATION = "AUTO_LOCATION"
    QR_CODE = "QR_CODE"
    MANUAL = "MANUAL"


class ListeningSaveResult(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"


class ListeningEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ListeningId
    installation_id: UUID
    poi_id: ReferenceId
    poi_content_id: ReferenceId
    trigger_type: ListeningTriggerType
    started_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    duration_sec: DurationSeconds | None = None

    @field_validator("id")
    @classmethod
    def validate_identifier_date(cls, value: str) -> str:
        try:
            datetime.strptime(value[7:13], "%d%m%y")
        except ValueError as exc:
            raise ValueError("id must contain a valid ddmmyy date") from exc
        return value

    @field_validator("started_at", "completed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_completion_time(self):
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")
        return self


class ListeningEventAck(BaseModel):
    id: str
    result: ListeningSaveResult


class QrScanCreate(BaseModel):
    """Record the start of a listening session triggered by a scanned QR code."""

    model_config = ConfigDict(extra="forbid")

    id: ListeningId
    installation_id: UUID
    qr_code: QrCode
    poi_content_id: ReferenceId
    scanned_at: AwareDatetime

    @field_validator("id")
    @classmethod
    def validate_identifier_date(cls, value: str) -> str:
        try:
            datetime.strptime(value[7:13], "%d%m%y")
        except ValueError as exc:
            raise ValueError("id must contain a valid ddmmyy date") from exc
        return value

    @field_validator("scanned_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class QrScanAck(ListeningEventAck):
    poi_id: str
    poi_content_id: str


class ListeningDashboardSummary(BaseModel):
    total_listening_sessions: int


class ListeningHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    installation_id: UUID
    poi_content_id: str
    poi_id: str
    trigger_type: str
    started_at: datetime
    completed_at: datetime | None
    duration_sec: int | None
    created_at: datetime
