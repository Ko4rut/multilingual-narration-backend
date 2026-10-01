from .db import get_engine
from .models import Base

if __name__ == "__main__":
    Base.metadata.create_all(get_engine())
