from collections.abc import Iterator
from sqlalchemy.orm import Session
from app.core.database import get_engine

def get_session() -> Iterator[Session]:
    # Services own write transactions; closing rolls back uncommitted work.
    with Session(get_engine()) as session:
        yield session
