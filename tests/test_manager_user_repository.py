from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.domains.identity.models.manager_user import ManagerUserModel
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


def test_list_has_stable_order_and_pagination():
    session = MagicMock(spec=Session)
    expected_users = [MagicMock(spec=ManagerUserModel)]
    session.scalars.return_value = expected_users
    repository = ManagerUserRepository(session)

    result = repository.list(offset=20, limit=10)

    assert result == expected_users
    statement = session.scalars.call_args.args[0]
    assert statement._offset_clause.value == 20
    assert statement._limit_clause.value == 10
    assert "ORDER BY manager_user.id" in str(statement)


def test_add_does_not_commit_the_service_transaction():
    session = MagicMock(spec=Session)
    manager_user = MagicMock(spec=ManagerUserModel)
    repository = ManagerUserRepository(session)

    result = repository.add(manager_user)

    assert result is None
    session.add.assert_called_once_with(manager_user)
    session.commit.assert_not_called()
