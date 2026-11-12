"""Verify the Listening Analytics permission seeded for new admin roles."""

from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import (
    Action, ManagementFunction, ManagerUser, Permission, Role, RolePermission,
)
from app.core.database import Base
from app.domains.identity.repositories.permission import PermissionRepository
from scripts.seed import seed_identity


def test_seed_assigns_listening_analytics_read_only_when_admin_role_is_new(
    monkeypatch,
):
    # Avoid expensive password hashing in this isolated RBAC seed test.
    monkeypatch.setattr(
        "scripts.seed.Argon2PasswordHasher",
        lambda: SimpleNamespace(hash_password=lambda password: "test-hash"),
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    models = (Action, ManagementFunction, Role, Permission, RolePermission, ManagerUser)
    Base.metadata.create_all(engine, tables=[model.__table__ for model in models])

    with Session(engine) as session, session.begin():
        seed_identity(session)
        role = session.scalar(select(Role).where(Role.name == "Super Administrator"))
        assert role is not None
        permissions = PermissionRepository(session)
        assert permissions.role_has_permission(
            role.id, function_name="Listening Analytics", action_name="read"
        )

        # Re-seeding must not restore permissions an administrator revoked.
        listening_function = session.scalar(
            select(ManagementFunction).where(
                ManagementFunction.name == "Listening Analytics"
            )
        )
        read_action = session.scalar(select(Action).where(Action.name == "read"))
        permission = session.scalar(
            select(Permission).where(
                Permission.function_id == listening_function.id,
                Permission.action_id == read_action.id,
            )
        )
        link = session.get(
            RolePermission, (permission.id, role.id),
        )
        assert link is not None
        session.delete(link)
        session.flush()

        seed_identity(session)
        assert not permissions.role_has_permission(
            role.id, function_name="Listening Analytics", action_name="read"
        )
