from __future__ import annotations

from contextlib import contextmanager

from app.core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = get_settings().database_url.get_secret_value()

class Base(DeclarativeBase):
    pass


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


@contextmanager
def session_scope():
    SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    with SessionLocal.begin() as session:
        yield session
