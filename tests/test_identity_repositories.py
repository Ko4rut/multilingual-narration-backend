from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.identity.models.user_session import UserSessionModel
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.user_session import UserSessionRepository


NOW = datetime(2026, 10, 26, 8, 30, tzinfo=timezone.utc)


def test_permission_lookup_joins_role_function_and_action():
    session = MagicMock(spec=Session)
    session.scalar.return_value = "perm-12345678"
    repository = PermissionRepository(session)

    result = repository.role_has_permission(
        "role-12345678",
        function_name="User Management",
        action_name="read",
    )

    assert result is True
    statement = session.scalar.call_args.args[0]
    statement_text = str(statement)
    assert "JOIN role_permission" in statement_text
    assert "JOIN management_function" in statement_text
    assert "JOIN action" in statement_text
    assert {
        "role-12345678",
        "User Management",
        "read",
    }.issubset(set(statement.compile().params.values()))


def test_revoke_all_active_sessions_updates_loaded_entities_without_commit():
    session = MagicMock(spec=Session)
    sessions = [
        UserSessionModel(
            id=f"sess-261026-0000000{index}",
            user_id="user-261026-12345678",
            refresh_token_hash=str(index) * 64,
            expires_at=NOW + timedelta(days=1),
            created_at=NOW,
            revoked_at=None,
        )
        for index in (1, 2)
    ]
    session.scalars.return_value = sessions
    repository = UserSessionRepository(session)

    repository.revoke_all_active_for_user(
        "user-261026-12345678",
        NOW,
    )

    assert all(user_session.revoked_at == NOW for user_session in sessions)
    session.commit.assert_not_called()


def test_refresh_token_lookup_for_rotation_locks_session_row():
    session = MagicMock(spec=Session)
    repository = UserSessionRepository(session)

    repository.get_by_refresh_token_hash_for_update("a" * 64)

    statement = session.scalar.call_args.args[0]
    assert "FOR UPDATE" in str(statement)
    assert "a" * 64 in statement.compile().params.values()
