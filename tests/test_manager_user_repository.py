from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)
from app.domains.identity.repositories.manager_user import ManagerUserRepository


def test_get_by_id_uses_session_identity_lookup():
    session = MagicMock(spec=Session)
    expected_user = MagicMock(spec=ManagerUserModel)
    session.get.return_value = expected_user
    repository = ManagerUserRepository(session)

    result = repository.get_by_id("user-010926-12345678")

    assert result is expected_user
    session.get.assert_called_once_with(
        ManagerUserModel,
        "user-010926-12345678",
    )


def test_get_by_email_filters_by_email():
    session = MagicMock(spec=Session)
    expected_user = MagicMock(spec=ManagerUserModel)
    session.scalar.return_value = expected_user
    repository = ManagerUserRepository(session)

    result = repository.get_by_email("admin@mnr.local")

    assert result is expected_user
    statement = session.scalar.call_args.args[0]
    assert statement.compile().params == {"email_1": "admin@mnr.local"}


def test_get_all_has_stable_order_and_pagination():
    session = MagicMock(spec=Session)
    expected_users = [MagicMock(spec=ManagerUserModel)]
    session.scalars.return_value = expected_users
    repository = ManagerUserRepository(session)

    result = repository.get_all(offset=20, limit=10)

    assert result == expected_users
    statement = session.scalars.call_args.args[0]
    assert statement._offset_clause.value == 20
    assert statement._limit_clause.value == 10
    assert (
        "ORDER BY manager_user.created_at, manager_user.id"
        in str(statement)
    )


def test_get_all_searches_identity_fields_and_filters_status():
    session = MagicMock(spec=Session)
    session.scalars.return_value = []
    repository = ManagerUserRepository(session)

    repository.get_all(
        offset=0,
        limit=20,
        search="admin%_",
        user_status=ManagerUserStatus.ACTIVE,
    )

    statement = session.scalars.call_args.args[0]
    statement_text = str(statement)
    parameters = statement.compile().params
    assert "manager_user.id" in statement_text
    assert "manager_user.email" in statement_text
    assert "manager_user.full_name" in statement_text
    assert "manager_user.user_status" in statement_text
    assert "%admin\\%\\_%" in parameters.values()
    assert ManagerUserStatus.ACTIVE in parameters.values()


def test_add_does_not_commit_the_service_transaction():
    session = MagicMock(spec=Session)
    manager_user = MagicMock(spec=ManagerUserModel)
    repository = ManagerUserRepository(session)

    result = repository.add(manager_user)

    assert result is None
    session.add.assert_called_once_with(manager_user)
    session.commit.assert_not_called()
