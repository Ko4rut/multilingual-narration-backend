from app.domains.identity.routers.identity import (
    auth_router,
    manager_user_router,
    role_router,
)

__all__ = ["auth_router", "manager_user_router", "role_router"]
