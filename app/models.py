from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Action(Base):
    __tablename__ = "action"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class ManagementFunction(Base):
    __tablename__ = "management_function"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class Permission(Base):
    __tablename__ = "permission"
    id: Mapped[int] = mapped_column(primary_key=True)
    function_id: Mapped[int] = mapped_column(ForeignKey("management_function.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("action.id", ondelete="RESTRICT"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("function_id", "action_id", name="uq_permission_function_action"),)


class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class RolePermission(Base):
    __tablename__ = "role_permission"
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)


class ManagementUser(Base):
    __tablename__ = "management_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id", ondelete="RESTRICT"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)


class Language(Base):
    __tablename__ = "language"
    id: Mapped[int] = mapped_column(primary_key=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PoiCategory(Base):
    __tablename__ = "poi_category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)


class PointOfInterest(Base):
    __tablename__ = "point_of_interest"
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id", ondelete="RESTRICT"), nullable=False, index=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    qr_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    poi_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    poi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    trigger_radius: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    poi_location: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PoiContent(Base):
    __tablename__ = "poi_content"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="CASCADE"), nullable=False, index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("language.id", ondelete="RESTRICT"), nullable=False, index=True)
    narration_title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration_script: Mapped[str] = mapped_column(Text, nullable=False)
    content_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("poi_id", "language_id", name="uq_poi_content_poi_language"),)


class ContentAudio(Base):
    __tablename__ = "content_audio"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_content_id: Mapped[int] = mapped_column(ForeignKey("poi_content.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    audio_size: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    checksum_sha25: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ListeningHistory(Base):
    __tablename__ = "listening_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="RESTRICT"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PoiCategoryMapping(Base):
    __tablename__ = "poi_category_mapping"
    poi_id: Mapped[int] = mapped_column(ForeignKey("point_of_interest.id", ondelete="CASCADE"), primary_key=True)
    poi_category_id: Mapped[int] = mapped_column(ForeignKey("poi_category.id", ondelete="CASCADE"), primary_key=True)


class OfflinePackage(Base):
    __tablename__ = "offline_package"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("poi_category.id", ondelete="RESTRICT"), nullable=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id", ondelete="RESTRICT"), nullable=False, index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("language.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    total_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("management_user.id", ondelete="RESTRICT"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
